"""Deterministic administration races, using only synthetic acceptance data."""
from playwright.sync_api import expect


def open_internal_admin(page, base, evidence):
    # Hold a feature dependency until app.js has executed. Startup must wait for
    # DOMContentLoaded, rather than treating an unloaded global as a lost session.
    held = []
    page.route('**/assets/paper.js', lambda route: held.append(route))
    try:
        page.goto(base+'/', wait_until='commit')
        page.wait_for_function("() => typeof state !== 'undefined'")
        evidence.checkpoint(page, 'startup-with-paper-pending')
        assert page.evaluate('() => state.me === null && pendingRequests === 0'), 'Startup ran before feature scripts were ready'
        assert held, 'paper.js must still be pending'
    finally:
        for route in held:
            route.continue_()
        page.unroute('**/assets/paper.js')
    page.wait_for_load_state('domcontentloaded')
    expect(page.locator('[data-view=home]')).to_have_attribute('aria-current', 'page')
    before = evidence.checkpoint(page, 'before-first-admin')
    assert before['path'] == '/' and before['session_status'] == 200
    assert before['account']['email'] == 'admin@example.local' and before['account']['admin'] is True
    page.locator('[data-view=admin]').click()
    expect(page.get_by_role('heading', name='Collaborateurs', exact=True)).to_be_visible()
    expect(page.locator('[data-view=admin]')).to_have_attribute('aria-current', 'page')
    evidence.checkpoint(page, 'first-admin-loaded')


def admin_during_refresh(page, base, launch_id, deputy_id, evidence):
    # The upload closes its modal before openLaunch's background refresh ends.
    # Keep its final request pending while the user chooses Administration.
    held = []
    pattern = f'**/api/launches/{launch_id}/supplier-requests'

    def hold(route):
        held.append(route)
        page.evaluate('window.__partnerRefreshHeld = true')

    page.route(pattern, hold)
    try:
        page.locator('#intake-confirm-form button[type=submit]').click()
        expect(page.locator('#intake-confirm-form')).to_have_count(0)
        page.wait_for_function('() => window.__partnerRefreshHeld === true')
        before = evidence.checkpoint(page, 'before-employee-admin')
        assert before['path'] == '/' and before['view'] == 'detail'
        assert before['session_status'] == 200 and before['account']['admin'] is True
        page.locator('[data-view=admin]').click()
        target = page.locator(f'[data-user-access="{deputy_id}"]')
        expect(target).to_be_visible()
        expect(target.locator('xpath=ancestor::tr')).to_contain_text('deputy@example.local')
        evidence.checkpoint(page, 'admin-loaded-with-collaborator')
        with page.expect_response(lambda response: response.url == base+f'/api/launches/{launch_id}/supplier-requests') as refresh:
            held.pop().continue_()
        assert refresh.value.ok
        # Wait for consumption as well as the HTTP response. This regression
        # check must observe the late refresh, not pass before it can remount.
        page.wait_for_function('() => pendingRequests === 0')
        expect(page.locator('[data-view=admin]')).to_have_attribute('aria-current', 'page')
        expect(target).to_be_visible()
        evidence.checkpoint(page, 'admin-preserved-after-stale-refresh')
    finally:
        for route in held:
            route.continue_()
        page.unroute(pattern)
