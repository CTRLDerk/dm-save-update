"""Window check for CI (needs Tk): lists fill, the selection is found, a preview runs.

Run from the repository root: python -m tests.gui_check
"""
import json
import os
import sys
import tempfile
import time

from tests.test_core import make_mod, write_save


def main():
    from dm_save_update import gui

    tmp = tempfile.mkdtemp()
    saves = os.path.join(tmp, 'Delta Manager', 'sauvegardes')
    write_save(os.path.join(saves, 'solo', 'slot_1'))
    write_save(os.path.join(saves, 'spectator', 'slot_2'))
    write_save(os.path.join(saves, 'solo', 'slot_3'))
    workshop = os.path.join(tmp, 'workshop', 'content', '4247780')
    os.makedirs(os.path.join(workshop, '123'))
    with open(os.path.join(workshop, '123', 'mod.json'), 'w', encoding='utf-8') as fh:
        json.dump(make_mod(), fh, indent=2)
    extra = os.path.join(tmp, 'mods with space', 'slot_5.json')
    os.makedirs(os.path.dirname(extra))
    with open(extra, 'w', encoding='utf-8') as fh:
        json.dump(make_mod(), fh)

    shown = []

    def fail(*args, **kw):
        raise AssertionError('dialog shown: %r' % (args,))

    def info(title, msg, **kw):
        if 'Choose a mod' in msg or 'choice changed' in msg:
            fail(msg)
        shown.append(msg)
    gui.messagebox.showerror = fail
    gui.messagebox.showinfo = info
    gui.messagebox.askyesno = lambda *a, **kw: True

    for name in gui.FONT_FILES + ('OFL-Barlow.txt',):
        assert os.path.isfile(os.path.join(gui.font_dir(), name)), name
    for name in ('icon.ico', 'icon.png'):
        assert os.path.isfile(os.path.join(gui.data_dir('assets'), name)), name

    app = gui.App()
    app.withdraw()
    app.saves_dir.set(saves)
    app.workshop_dir.set(workshop)
    app.refresh_lists()
    assert len(app.saves) == 3 and len(app.mods) == 1, (app.saves, app.mods)
    assert app.sel['save'] == 0 and len(app.save_rows) == 3, app.sel
    modes = [s['mode'] for s in app.saves]
    assert modes == sorted(modes, key=('solo', 'coop', 'spectator').index), modes  # one group per mode
    app.choose_save([s['slot'] for s in app.saves].index('slot_1'))

    # A mod file picked by hand (Windows path with backslashes) must stay selectable.
    gui.filedialog.askopenfilename = lambda **kw: extra
    app.pick_mod_file()
    assert app.mod_box.get() == app.mods[0]['label'], app.mod_box.get()
    assert '\\' not in app.mods[0]['label']

    for idx in (0, 1):  # both the picked file and the Workshop mod
        app.mod_box.current(idx)
        app.mod_box.event_generate('<<ComboboxSelected>>')
        app.update()
        app.changes = []
        app.status.set('')
        app.run_compare()
        deadline = time.time() + 20
        while not app.status.get().startswith('Preview') and time.time() < deadline:
            app.update()
            time.sleep(0.05)
        assert app.status.get().startswith('Preview'), app.status.get()
        assert app.changes, 'no changes found'
        print('mod %d: %s' % (idx, app.status.get()))

    # Filters: action, category and free text narrow the table; Clear shows everything again.
    total = len(app.changes)
    assert len(app.tree.get_children()) == total
    app.filter_action.set('Update')
    app.fill_tree()
    rows = app.tree.get_children()
    assert rows and all(app.tree.item(r, 'tags')[0] == 'update' for r in rows)
    cat = app.filter_boxes['CATEGORY']['values'][1]
    app.filter_cat.set(cat)
    app.fill_tree()
    assert all(app.tree.set(r, 'category') == cat for r in app.tree.get_children())
    app.filter_text.set('no-such-field-xyz')
    app.fill_tree()
    assert not app.tree.get_children() and app.shown.get() == '0 of %d shown' % total, app.shown.get()
    app.clear_filters()
    assert len(app.tree.get_children()) == total

    # A save that already matches the mod: the table says so instead of staying empty.
    app.show_result([], [], ('m', 's'))
    rows = app.tree.get_children()
    assert len(rows) == 1 and app.tree.item(rows[0], 'tags')[0] == 'done', rows

    # Apply the last preview, then the preview must show no updates and a backup must exist.
    assert str(app.apply_btn['state']) == 'normal'
    app.status.set('')
    app.run_apply()
    deadline = time.time() + 20
    while not (app.status.get().startswith('Preview') and app.notes and app.notes[0].startswith('Applied')) \
            and time.time() < deadline:
        app.update()
        time.sleep(0.05)
    assert app.notes and app.notes[0].startswith('Applied'), (app.status.get(), app.notes[:1])
    left = [c for c in app.changes if c.action == 'update']
    assert not left, [(c.category, c.path) for c in left]
    assert str(app.apply_btn['state']) == 'disabled'
    slot = os.path.join(saves, 'solo', 'slot_1')
    assert any(n.startswith('_dmsu_backup_') for n in os.listdir(slot)), os.listdir(slot)
    print('apply: %s' % app.notes[0])
    app.destroy()
    print('window check ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
