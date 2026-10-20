"""Translate the two folder switches into existing, server-enforced grants."""
FOLDER_SLUGS = ('jaune', 'rose', 'bleu', 'vert')
READ_ACTIONS = ('document.read', 'rex.read')
MODIFY_ACTIONS = ('document.write', 'rex.write', 'completeness.review',
                  'document.review', 'value.write', 'impact.review',
                  'quality.review', 'requirement.review', 'ambiguity.review')


def folder_grants(settings):
    grants = []
    for slug in FOLDER_SLUGS:
        flags = settings.get(slug)
        if not flags or not flags.access:
            continue
        grants.extend((action, slug) for action in READ_ACTIONS)
        if flags.modify:
            grants.extend((action, slug) for action in MODIFY_ACTIONS)
            if slug == 'rose':
                grants.append(('commitment.review', slug))
    return grants


def folder_access(role):
    admin = role.name == 'Administrateur'
    def has(action, slug):
        return admin or any(g.action == action and g.folder_slug in (None, slug)
                            for g in role.grants)
    return {slug: {'access': has('document.read', slug),
                   'modify': has('document.read', slug) and has('document.write', slug)}
            for slug in FOLDER_SLUGS}
