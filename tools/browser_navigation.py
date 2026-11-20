"""Drive the same visible sidebar controls as an employee or administrator."""


def select_sidebar_view(page, view):
    sidebar = page.locator('.sidebar')
    sidebar.wait_for()
    mobile_toggle = sidebar.get_by_role('button', name='Menu', exact=True)
    if mobile_toggle.is_visible() and mobile_toggle.get_attribute('aria-expanded') == 'false':
        mobile_toggle.click()
    item = sidebar.locator(f'[data-view="{view}"]')
    group = item.locator('xpath=ancestor::details[1]')
    if group.count() and group.get_attribute('open') is None:
        group.locator('summary').click()
    item.click()
