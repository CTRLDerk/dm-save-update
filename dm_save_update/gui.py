"""Window: pick the save folder and the Workshop folder, choose a mod and a save, preview and apply the update."""
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__, apply, core, steam

ACTION_TAGS = {
    core.UPDATE: 'update',
    core.KEEP_ERA: 'keep',
    core.KEEP_MAJOR: 'keep',
    core.KEEP_GAME: 'keep',
    core.NOT_ADDED: 'skip',
    core.NOT_IN_MOD: 'skip',
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('DM Save Update %s' % __version__)
        self.geometry('1180x720')
        self.minsize(900, 560)
        self.saves, self.mods, self.extra_mods = [], [], []
        self.sel = {'mod': -1, 'save': -1}
        self.changes, self.notes = [], []
        self.preview = None  # what 'Apply' will write: set by a preview
        self.saves_dir = tk.StringVar(value=steam.find_saves_dir())
        self.workshop_dir = tk.StringVar(value=steam.find_workshop_dir())
        self.overwrite_era = tk.BooleanVar(value=False)
        self.overwrite_major = tk.BooleanVar(value=False)
        self.show_kept = tk.BooleanVar(value=True)
        self.status = tk.StringVar()
        self._build()
        self.refresh_lists()

    # ------------------------------------------------------------- layout
    def _build(self):
        pad = {'padx': 8, 'pady': 4}
        top = ttk.Frame(self)
        top.pack(fill='x', **pad)
        for row, (label, var) in enumerate((('Save folder (sauvegardes)', self.saves_dir),
                                            ('Workshop folder (content\\%s)' % core.APP_ID, self.workshop_dir))):
            ttk.Label(top, text=label).grid(row=row, column=0, sticky='w')
            ttk.Entry(top, textvariable=var).grid(row=row, column=1, sticky='ew', padx=6)
            ttk.Button(top, text='Browse…', command=lambda v=var: self.browse(v)).grid(row=row, column=2)
        ttk.Button(top, text='Reload', command=self.refresh_lists).grid(row=0, column=3, rowspan=2, padx=6, sticky='ns')
        top.columnconfigure(1, weight=1)

        picks = ttk.Frame(self)
        picks.pack(fill='x', **pad)
        ttk.Label(picks, text='Mod (new version)').grid(row=0, column=0, sticky='w')
        self.mod_box = ttk.Combobox(picks, state='readonly')
        self.mod_box.grid(row=0, column=1, sticky='ew', padx=6)
        ttk.Button(picks, text='Other mod file…', command=self.pick_mod_file).grid(row=0, column=2)
        ttk.Label(picks, text='Save').grid(row=1, column=0, sticky='w')
        self.save_box = ttk.Combobox(picks, state='readonly')
        self.save_box.grid(row=1, column=1, sticky='ew', padx=6)
        self.mod_box.bind('<<ComboboxSelected>>', lambda e: self._remember_choice('mod'))
        self.save_box.bind('<<ComboboxSelected>>', lambda e: self._remember_choice('save'))
        picks.columnconfigure(1, weight=1)

        opts = ttk.Frame(self)
        opts.pack(fill='x', **pad)
        ttk.Checkbutton(opts, text='Also overwrite rules changed by era votes in this career',
                        variable=self.overwrite_era).pack(side='left')
        ttk.Checkbutton(opts, text='Also overwrite values drawn at a major regulation',
                        variable=self.overwrite_major).pack(side='left', padx=12)
        ttk.Checkbutton(opts, text='Show kept and skipped items', variable=self.show_kept,
                        command=self.fill_tree).pack(side='left', padx=12)
        ttk.Button(opts, text='Show changes', command=self.run_compare).pack(side='right')

        acts = ttk.Frame(self)
        acts.pack(fill='x', **pad)
        self.apply_btn = ttk.Button(acts, text='Apply update', command=self.run_apply, state='disabled')
        self.apply_btn.pack(side='right')
        ttk.Button(acts, text='Restore backup…', command=self.open_restore).pack(side='right', padx=6)
        ttk.Button(acts, text='Save report…', command=self.save_report).pack(side='right')
        ttk.Label(acts, text='Close Delta Manager (or go back to its main menu) before you apply or restore. '
                             'A backup is made in the save folder first.').pack(side='left')

        self.note_box = tk.Text(self, height=4, wrap='word', relief='flat', background=self.cget('background'))
        self.note_box.pack(fill='x', **pad)

        cols = ('category', 'section', 'item', 'field', 'save', 'mod', 'action')
        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True, **pad)
        self.tree = ttk.Treeview(frame, columns=cols, show='headings')
        widths = (170, 90, 210, 220, 190, 190, 120)
        for c, w in zip(cols, widths):
            self.tree.heading(c, text=c.capitalize() if c not in ('save', 'mod') else c.capitalize() + ' value')
            self.tree.column(c, width=w, stretch=c in ('item', 'field', 'save', 'mod'))
        ysb = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        ysb.pack(side='right', fill='y')
        self.tree.tag_configure('keep', foreground='#8a6d00')
        self.tree.tag_configure('skip', foreground='#888888')
        ttk.Label(self, textvariable=self.status, anchor='w').pack(fill='x', **pad)

    # ------------------------------------------------------------- actions
    def browse(self, var):
        path = filedialog.askdirectory(initialdir=var.get() or os.path.expanduser('~'))
        if path:
            var.set(os.path.normpath(path))
            self.refresh_lists()

    def pick_mod_file(self):
        path = filedialog.askopenfilename(filetypes=[('Mod file', '*.json')])
        if path:
            path = os.path.normpath(path)
            name = steam.peek_mod_name(path) or os.path.basename(path)
            # No backslashes in a label: Tk mangles them in a combobox list.
            where = '/'.join(path.replace('\\', '/').split('/')[-2:])
            self.extra_mods = [m for m in self.extra_mods if m['path'] != path]
            self.extra_mods.insert(0, {'path': path, 'item': '', 'label': '%s  (file %s)' % (name, where)})
            self._fill_mod_list(select=0)

    def _fill_mod_list(self, select=0):
        self.mods = self.extra_mods + steam.list_workshop_mods(self.workshop_dir.get())
        self.mod_box['values'] = [m['label'] for m in self.mods]
        self._select_entry('mod', self.mod_box, select if self.mods else -1)

    def _select_entry(self, which, box, index):
        self.sel[which] = index
        if index >= 0:
            box.current(index)
        else:
            box.set('')

    def _remember_choice(self, which):
        box, items = (self.mod_box, self.mods) if which == 'mod' else (self.save_box, self.saves)
        self.sel[which] = self._entry_index(box, items, self.sel[which])

    @staticmethod
    def _entry_index(box, items, fallback):
        text = box.get()
        for i, item in enumerate(items):
            if item['label'] == text:
                return i
        i = box.current()
        return i if i >= 0 else fallback

    def refresh_lists(self):
        self.saves = steam.list_saves(self.saves_dir.get())
        self.save_box['values'] = [s['label'] for s in self.saves]
        self._select_entry('save', self.save_box, 0 if self.saves else -1)
        self._fill_mod_list(select=0)
        self.status.set('%d saves, %d mods found.' % (len(self.saves), len(self.mods)))

    def _run_in_thread(self, work, done):
        """Run work() in a thread and done(result) in the window; Tk may only be used from the main thread."""
        box = queue.Queue()

        def run():
            try:
                box.put((work(), None))
            except Exception as exc:  # shown to the user, the window stays usable
                box.put((None, exc))

        def poll():
            try:
                result, error = box.get_nowait()
            except queue.Empty:
                self.after(100, poll)
                return
            self.config(cursor='')
            done(result, error)

        self.config(cursor='watch')
        threading.Thread(target=run, daemon=True).start()
        self.after(100, poll)

    def _chosen_entries(self):
        mi = self._entry_index(self.mod_box, self.mods, self.sel['mod'])
        si = self._entry_index(self.save_box, self.saves, self.sel['save'])
        if not (0 <= mi < len(self.mods)) or not (0 <= si < len(self.saves)):
            messagebox.showinfo('DM Save Update', 'Choose a mod and a save first.')
            return None
        return self.mods[mi], self.saves[si]

    def _compare_options(self):
        return core.Options(self.overwrite_era.get(), self.overwrite_major.get())

    def run_compare(self, after_apply=None):
        choice = self._chosen_entries()
        if not choice:
            return
        mod_entry, save_entry = choice
        opts = self._compare_options()
        self.preview = None
        self.apply_btn.config(state='disabled')
        self.status.set('Reading the mod and the save…')

        def work():
            mod = core.load_json(mod_entry['path'])
            save = core.Save(save_entry['path'])
            found, _ = core.match_score(mod, save)
            changes, notes = core.compare(mod, save, opts)
            if found == 0:
                notes.insert(0, 'None of the mod\'s categories are in this save. This save probably belongs to '
                                'another mod.')
            return mod, save, changes, notes

        def done(result, error):
            if error is not None:
                self.status.set('Could not read the files: %s' % error)
                messagebox.showerror('DM Save Update', str(error))
                return
            mod, save, changes, notes = result
            label = (mod_entry['label'], save_entry['label'])
            if after_apply:
                notes = [after_apply] + notes
            self.show_result(changes, notes, label)
            updates = sum(1 for c in changes if c.action == core.UPDATE)
            if updates:
                self.preview = {'mod': mod, 'mod_entry': mod_entry, 'save_entry': save_entry, 'mtime': save.mtime,
                                'options': (opts.overwrite_era, opts.overwrite_major), 'updates': updates}
                self.apply_btn.config(state='normal')

        self._run_in_thread(work, done)

    def show_result(self, changes, notes, label):
        self.changes, self.notes, self.result_labels = changes, notes, label
        self.note_box.delete('1.0', 'end')
        self.note_box.insert('end', '\n'.join(notes) or 'No notes.')
        self.fill_tree()
        counts = core.summary(changes)
        self.status.set('Preview: ' + (', '.join('%s %d' % kv for kv in sorted(counts.items())) or 'no differences')
                        + '.')

    def run_apply(self):
        pv = self.preview
        if not pv:
            return
        choice = self._chosen_entries()
        opts = self._compare_options()
        if (not choice or choice[0] is not pv['mod_entry'] or choice[1] is not pv['save_entry']
                or (opts.overwrite_era, opts.overwrite_major) != pv['options']):
            messagebox.showinfo('DM Save Update', 'The choice changed after the preview. Press "Show changes" again.')
            return
        save_entry = pv['save_entry']
        if not messagebox.askyesno('DM Save Update', (
                'Apply %d updates to\n%s\n\nfrom\n%s?\n\nClose Delta Manager first (or go back to its main menu). '
                'Your career progress is not touched. A backup of config.json, season.json and meta.json is made in '
                'the save folder, and "Restore backup…" puts it back.')
                % (pv['updates'], save_entry['label'], pv['mod_entry']['label'])):
            return
        self.apply_btn.config(state='disabled')
        self.status.set('Writing the update…')

        def work():
            return apply.apply_update(pv['mod'], save_entry['path'], opts, pv['mod_entry']['label'],
                                      expect_mtime=pv['mtime'])

        def done(result, error):
            if error is not None:
                self.status.set('Not applied: %s' % error)
                messagebox.showerror('DM Save Update', 'Nothing was written.\n\n%s' % error)
                return
            applied, _, backup = result
            msg = 'Applied %d updates. Backup: %s' % (len(applied), backup or '-')
            messagebox.showinfo('DM Save Update', msg)
            self.run_compare(after_apply=msg)  # the preview now shows what is left (should be no updates)

        self._run_in_thread(work, done)

    def open_restore(self):
        choice = self._chosen_entries()
        if not choice:
            return
        save_entry = choice[1]
        backups = apply.list_backups(save_entry['path'])
        if not backups:
            messagebox.showinfo('DM Save Update', 'This save has no backups made by DM Save Update.')
            return
        win = tk.Toplevel(self)
        win.title('Restore backup - %s' % save_entry['label'])
        win.transient(self)
        ttk.Label(win, text='Backups of this save, newest first. Restoring puts config.json, season.json and '
                            'meta.json back; the current files are backed up first.', wraplength=560).pack(padx=10, pady=6)
        lb = tk.Listbox(win, width=90, height=min(12, len(backups)))
        for folder, info in backups:
            lb.insert('end', '%s   %s' % (os.path.basename(folder), info.get('mod') or ''))
        lb.selection_set(0)
        lb.pack(padx=10, pady=4, fill='both', expand=True)

        def do_restore():
            sel = lb.curselection()
            if not sel:
                return
            folder = backups[sel[0]][0]
            if not messagebox.askyesno('DM Save Update', 'Put back %s?\n\nClose Delta Manager first.'
                                       % os.path.basename(folder), parent=win):
                return
            try:
                restored, undo = apply.restore_backup(save_entry['path'], folder)
            except Exception as exc:
                messagebox.showerror('DM Save Update', str(exc), parent=win)
                return
            win.destroy()
            msg = 'Restored %s from %s. The files from before the restore are in %s.' % (
                ', '.join(restored), os.path.basename(folder), os.path.basename(undo))
            messagebox.showinfo('DM Save Update', msg)
            self.run_compare(after_apply=msg)

        ttk.Button(win, text='Restore', command=do_restore).pack(side='right', padx=10, pady=8)
        ttk.Button(win, text='Cancel', command=win.destroy).pack(side='right', pady=8)

    def fill_tree(self):
        self.tree.delete(*self.tree.get_children())
        for c in self.changes:
            tag = ACTION_TAGS.get(c.action, 'update')
            if tag != 'update' and not self.show_kept.get():
                continue
            self.tree.insert('', 'end', tags=(tag,), values=(
                c.category, c.section, c.item, c.path, core.short(c.old, 60), core.short(c.new, 60),
                c.action + (' *' if c.note else '')))

    def save_report(self):
        if not self.changes and not self.notes:
            messagebox.showinfo('DM Save Update', 'Press "Show changes" first.')
            return
        path = filedialog.asksaveasfilename(defaultextension='.txt', initialfile='dm-save-update-report.txt',
                                            filetypes=[('Text', '*.txt')])
        if path:
            mod_label, save_label = self.result_labels
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(core.report_text(self.changes, self.notes, mod_label, save_label))
            self.status.set('Report saved: %s' % path)


def main():
    App().mainloop()
