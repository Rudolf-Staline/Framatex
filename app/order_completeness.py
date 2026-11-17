"""Order adapter over the shared evaluator, preserving historical launch scope."""
from sqlalchemy import select
from .models import Launch
from .access import accessible
from .order_documents import OrderCompleteness
from .completeness_models import LaunchCompleteness
from .partner_phase2_models import BusinessOrderLaunch
from .completeness import evaluate_context, report_summary


def evaluate(db, order, user, permitted):
    context = db.get(OrderCompleteness, order.id)
    report = evaluate_context(db, 'order', order, context, user, permitted)
    launches = list(db.scalars(select(Launch).join(BusinessOrderLaunch).where(BusinessOrderLaunch.order_id == order.id)))
    for launch in launches:
        if not accessible(db, user, launch):
            report['partial_visibility'] = True
            continue
        legacy = db.get(LaunchCompleteness, launch.id)
        if not legacy or not legacy.profile_id: continue
        inherited = evaluate_context(db, 'launch', launch, legacy, user, permitted)
        report['configured'] = report['configured'] or inherited['configured']
        report['partial_visibility'] = report['partial_visibility'] or inherited['partial_visibility']
        report['rows'].extend(inherited['rows'])
    # An explicitly order-scoped rule attached to several launches is one
    # obligation; launch-scoped rules and their exceptions remain separate.
    report['rows'] = list({r['obligation_key']: r for r in report['rows']}.values())
    report['order_id'] = order.id
    report_summary(report)
    # Compatibility contract: order UI historically used ready/items, while
    # launch consumers used present/rows. Both are backed by identical rows.
    report['counts']['ready'] = report['counts']['present']
    report['items'] = [{**r, 'status': 'ready' if r['status'] == 'present' else r['status'],
        'doc_type': r['document_type'], 'deadline': r['due_date'],
        'documents': [d['id'] for d in r['documents']]} for r in report['rows']]
    return report
