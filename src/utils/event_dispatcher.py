"""
Event dispatcher: render templates and send via bot.
Use `send_event(bot, chat_id, event_key, context)` to replace direct sends.
"""
import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from src.utils import message_templates, event_registry
from src.utils import followup_manager
from src.database.connection import execute_query
from src.config import SUPER_ADMIN_USER_ID, USE_LOCAL_DB
from src.utils.role_notifications import get_moderator_chat_ids
import logging

logger = logging.getLogger(__name__)


def _render(text, context_vars):
    # Replace {{key}} with provided values only; leave missing as empty string
    if not text:
        return ''
    out = text
    i = 0
    while True:
        a = out.find('{{', i)
        if a == -1:
            break
        b = out.find('}}', a)
        if b == -1:
            break
        key = out[a+2:b].strip()
        val = ''
        if key in context_vars and context_vars[key] is not None:
            val = str(context_vars[key])
        out = out[:a] + val + out[b+2:]
        i = a + len(val)
    return out


def render_event(event_key, context_vars=None):
    """Render template for an event and return (text, buttons)
    Buttons are returned as list-of-rows where each row is list of dicts {text, callback_data}.
    """
    context_vars = context_vars or {}
    tpl = message_templates.get_template(event_key)
    if not tpl or not tpl.get('enabled'):
        text = event_registry.DEFAULT_TEMPLATES.get(event_key, '')
        buttons = []
    else:
        text = tpl.get('text', '')
        buttons = tpl.get('buttons', [])
    try:
        rendered = _render(text, context_vars)
    except Exception:
        rendered = event_registry.DEFAULT_TEMPLATES.get(event_key, '')
    return rendered, buttons


async def send_event(bot, chat_id, event_key, context_vars=None, parse_mode='Markdown', reply_markup=None):
    context_vars = context_vars or {}
    # load template
    # reuse render helper
    rendered, tpl_buttons = render_event(event_key, context_vars)

    # If caller provided explicit reply_markup, prefer it. Else build from template buttons if present.
    final_reply_markup = reply_markup
    if final_reply_markup is None and tpl_buttons:
        try:
            keyboard = []
            for row in tpl_buttons:
                r = []
                for b in row:
                    r.append(InlineKeyboardButton(b.get('text', 'Button'), callback_data=b.get('callback_data','')))
                keyboard.append(r)
            final_reply_markup = InlineKeyboardMarkup(keyboard)
        except Exception:
            logger.exception('Invalid buttons for event %s', event_key)
            final_reply_markup = None

    try:
        await bot.send_message(chat_id=chat_id, text=rendered, reply_markup=final_reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logger.error('Failed to send event %s to %s: %s', event_key, chat_id, e)


def schedule_followups(application, chat_id, event_key, context_vars=None):
    """Schedule follow-up steps from followup_manager for this event_key and chat_id.
    Idempotent: avoids scheduling jobs with the same name.
    """
    if not application:
        return
    seq = followup_manager.get_followups(event_key)
    if not seq:
        return
    for idx, step in enumerate(seq):
        # Allow caller to add an override delay (in hours) via context_vars
        base_delay_hours = int(step.get('delay_hours', 0) or 0)
        override_hours = int((context_vars or {}).get('delay_hours', 0) or 0)
        delay = int((base_delay_hours + override_hours) * 3600)
        tpl = step.get('template')
        if tpl not in event_registry.EVENT_KEYS:
            continue
        job_name = f"followup:{chat_id}:{event_key}:{idx}"
        # avoid duplicate jobs
        existing = application.job_queue.get_jobs_by_name(job_name)
        if existing:
            continue

        async def _followup_job(ctx):
            # ctx.job.data contains our payload
            data = ctx.job.data or {}
            chat = data.get('chat_id')
            tpl_key = data.get('template')
            ctx_vars = data.get('context_vars') or {}

            # Stop condition: if order_id present and payment completed, skip
            try:
                order_id = ctx_vars.get('order_id')
                if order_id:
                    # Stop followups only when outstanding balance == 0 or order is closed/paid
                    res = execute_query("SELECT payment_status, balance FROM store_orders WHERE order_id = %s", (order_id,), fetch_one=True)
                    try:
                        balance = float(res.get('balance') or 0) if res else 0
                    except Exception:
                        balance = 0
                    if (res and ((balance == 0) or (res.get('payment_status') and res.get('payment_status').upper() in ('PAID','COMPLETED','CLOSED')))):
                        logger.info(f"Skipping followup {tpl_key} for order {order_id} (no outstanding balance or closed)")
                        return
            except Exception:
                logger.debug('Followup stop-check failed; proceeding')

            # send the templated event
            try:
                await send_event(ctx.application.bot, chat, tpl_key, ctx_vars)
                logger.info(f"[FOLLOWUP] sent template={tpl_key} to user={chat}")

                # ALSO: send admin copies for visibility (must include user/name/id/context/amount)
                try:
                    admin_msg = (
                        f"🔔 Follow-up sent to {ctx_vars.get('name','Unknown')} ({chat})\n"
                        f"Reason: {tpl_key}\n"
                    )
                    amount = ctx_vars.get('amount')
                    if amount is not None:
                        admin_msg += f"Amount Due: ₹{amount}\n"

                    # Always notify SUPER_ADMIN_USER_ID if configured
                    if SUPER_ADMIN_USER_ID:
                        try:
                            await ctx.application.bot.send_message(chat_id=int(SUPER_ADMIN_USER_ID), text=admin_msg)
                            logger.info(f"[FOLLOWUP][ADMIN] sent to super_admin={SUPER_ADMIN_USER_ID} for user={chat}")
                        except Exception as aerr:
                            logger.debug(f"Could not send followup admin copy to SUPER_ADMIN_USER_ID: {aerr}")

                    # Notify other admins only when NOT in local-only mode to avoid DB access
                    if not USE_LOCAL_DB:
                        try:
                            # get_admin_chat_ids may query DB; call only when remote DB allowed
                            admin_chats = get_admin_chat_ids()
                            for ac in admin_chats:
                                if ac and int(ac) != int(SUPER_ADMIN_USER_ID or 0):
                                    try:
                                        await ctx.application.bot.send_message(chat_id=int(ac), text=admin_msg)
                                    except Exception:
                                        pass
                            logger.info(f"[FOLLOWUP][ADMIN] sent copies to admins for user={chat}")
                        except Exception as aderr:
                            logger.debug(f"Could not fetch/send admin list copies: {aderr}")
                except Exception as adm_exc:
                    logger.debug(f"Failed to send admin followup copy: {adm_exc}")

            except Exception as e:
                logger.error(f"Error running followup job {job_name}: {e}")

        # schedule job with payload
        application.job_queue.run_once(_followup_job, delay, name=job_name, data={'chat_id': chat_id, 'template': tpl, 'context_vars': context_vars or {}})
