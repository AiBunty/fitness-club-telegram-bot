"""
Event dispatcher: render templates and send via bot.
Use `send_event(bot, chat_id, event_key, context)` to replace direct sends.
"""
import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from src.utils import message_templates, event_registry
from src.utils import followup_manager
from src.database.connection import execute_query

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
        delay = int(step.get('delay_hours', 0) * 3600)
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
                    res = execute_query("SELECT payment_status FROM store_orders WHERE order_id = %s", (order_id,), fetch_one=True)
                    if res and res.get('payment_status') and res.get('payment_status').upper() in ('PAID','COMPLETED','CLOSED'):
                        logger.info(f"Skipping followup {tpl_key} for order {order_id} (payment completed)")
                        return
            except Exception:
                logger.debug('Followup stop-check failed; proceeding')

            # send the templated event
            try:
                await send_event(ctx.application.bot, chat, tpl_key, ctx_vars)
            except Exception as e:
                logger.error(f"Error running followup job {job_name}: {e}")

        # schedule job with payload
        application.job_queue.run_once(_followup_job, delay, name=job_name, data={'chat_id': chat_id, 'template': tpl, 'context_vars': context_vars or {}})
