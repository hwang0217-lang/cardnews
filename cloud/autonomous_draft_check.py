"""One bounded server draft call. Does not register designs or publish."""
import json
from pathlib import Path
from gemini_editor import generate_json, draft_prompt, validate_draft, MODEL

draft, usage = generate_json(draft_prompt([]))
validate_draft(draft)
out = Path('cloud-reports'); out.mkdir(exist_ok=True)
(out / 'autonomous-draft.json').write_text(json.dumps({'model': MODEL, 'draft': draft,
    'usage': usage, 'generated_in_cloud': True, 'published': False,
    'recent_feed_compared': False, 'purpose': 'provider capability preview only; not publishable'},
    ensure_ascii=False, indent=2), encoding='utf-8')
print('One server editorial draft complete; no design registration or publication')
