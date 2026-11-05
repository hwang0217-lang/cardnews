"""Project registration is independent of publishing approval and account authentication."""
import json
import re
from pathlib import Path

BLOCKED_DRAFTS = {'DAHZ8Qpyi7o', 'DAHZ8Shb8Lw', 'DAHZ8iwBTag'}

def require_registered(registry, plan):
    design = plan.get('canva_design_id', '')
    entry = registry.get('designs', {}).get(design, {})
    if (registry.get('version') != 1 or registry.get('project') != 'nordic' or
            registry.get('account') != 'nordic_log' or plan.get('account') != 'nordic_log' or
            not re.fullmatch(r'DA[A-Za-z0-9_-]{6,40}', design) or design in BLOCKED_DRAFTS or
            entry.get('active') is not True or entry.get('format') not in ('mp4', 'jpg') or
            entry.get('purpose') not in ('production', 'diagnostic') or
            plan.get('purpose') != entry.get('purpose') or
            plan.get('export_format', 'mp4') != entry.get('format')):
        raise RuntimeError('Design not registered for this Nordic plan')
    if entry['format'] == 'jpg' and (type(entry.get('page_count')) is not int or
            not 2 <= entry['page_count'] <= 10 or entry['page_count'] != plan.get('page_count')):
        raise RuntimeError('Carousel page count mismatch')
    return entry

def load_plan(root, requested, day):
    relative = requested or f'cloud/plans/{day}.json'
    if not re.fullmatch(r'cloud/(?:plans/[A-Za-z0-9_-]+|reel-plan)\.json', relative):
        raise RuntimeError('Plan must be a saved cloud plan path')
    path = Path(root) / relative
    if not path.is_file():
        raise RuntimeError('No reviewed plan for this day; do not reuse old content')
    plan = json.loads(path.read_text(encoding='utf-8'))
    require_registered(json.loads((Path(root) / 'cloud/design-registry.json').read_text(encoding='utf-8')), plan)
    return plan
