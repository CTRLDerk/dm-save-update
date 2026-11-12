"""Window: pick the save folder and the Workshop folder, choose a mod and a save, preview and apply the update.

Look: the DM Save Card style (Delta Manager redesign) - dark top bar with the red/green slash, chequered strip,
pit-wall panels with // headings, red hero for the chosen save, red = act, gold = kept, Barlow fonts.
"""
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

from . import __version__, apply, core, steam

ACTION_TAGS = {
    core.UPDATE: 'update',
    core.KEEP_ERA: 'keep',
    core.KEEP_MAJOR: 'keep',
    core.KEEP_GAME: 'keep',
    core.NOT_ADDED: 'skip',
    core.NOT_IN_MOD: 'skip',
}

P = {
    'top': '#0F0D0B', 'asphalt': '#15120F', 'pit': '#1E1A16', 'raised': '#29231D', 'row': '#2A241E',
    'row2': '#25201B', 'line': '#3A322A', 'edge': '#5A4E42', 'chrome': '#F4EDE2', 'muted': '#B3A797', 'faint': '#8C8070',
    'red': '#E2372B', 'red_dark': '#C92D22', 'red_shade': '#B02B22', 'red_tile': '#93241C', 'red_off': '#5A2620',
    'red_text': '#FF6A55', 'green': '#3DC36B', 'gold': '#F5C04A',
}
FONT_FILES = ('Barlow-Regular.ttf', 'Barlow-SemiBold.ttf', 'BarlowCondensed-Bold.ttf',
              'BarlowCondensed-ExtraBoldItalic.ttf')
MODE_NAMES = {'solo': 'SOLO', 'coop': 'CO-OP', 'multi': 'CO-OP', 'spectator': 'SPECTATOR', '': 'SAVES'}


def font_dir():
    base = getattr(sys, '_MEIPASS', None)
    if base:
        return os.path.join(base, 'dm_save_update', 'fonts')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')


def load_fonts():
    """Make the bundled Barlow fonts available to this process only (Windows); elsewhere system fonts are used."""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        for name in FONT_FILES:
            path = os.path.join(font_dir(), name)
            if os.path.isfile(path):
                ctypes.windll.gdi32.AddFontResourceExW(path, 0x10, 0)  # FR_PRIVATE
    except Exception:
        pass


def dark_title_bar(win):
    """Dark Windows title bar to match the window; ignored where not supported."""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        on = ctypes.c_int(1)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (newer, older Windows 10)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on), ctypes.sizeof(on)) == 0:
                break
    except Exception:
        pass


class App(tk.Tk):
    def __init__(self):
        load_fonts()
        super().__init__()
        self.title('DM Save Update %s' % __version__)
        self.geometry('1280x800')
        self.minsize(1040, 640)
        self.configure(bg=P['asphalt'])
        self.saves, self.mods, self.extra_mods = [], [], []
        self.sel = {'mod': -1, 'save': -1}
        self.changes, self.notes = [], []
        self.counts = None
        self.preview = None  # what 'Apply' will write: set by a preview
        self.saves_dir = tk.StringVar(value=steam.find_saves_dir())
        self.workshop_dir = tk.StringVar(value=steam.find_workshop_dir())
        self.overwrite_era = tk.BooleanVar(value=False)
        self.overwrite_major = tk.BooleanVar(value=False)
        self.show_kept = tk.BooleanVar(value=True)
        self.status = tk.StringVar()
        self._fonts()
        self._style()
        self._build()
        dark_title_bar(self)
        self.refresh_lists()

    # ------------------------------------------------------------- look
    def _fonts(self):
        fams = set(tkfont.families(self))

        def pick(name, fallback):
            return name if name in fams else fallback
        text = pick('Barlow', 'Segoe UI')
        semi = pick('Barlow SemiBold', text)
        cond = pick('Barlow Condensed', 'Arial Narrow')
        xcond = pick('Barlow Condensed ExtraBold', cond)
        xw = 'normal' if xcond != cond else 'bold'  # the ExtraBold family is already heavy
        self.f = {
            'text': (text, 10), 'small': (text, 9), 'semi': (semi, 10), 'cap': (semi, 8),
            'cond': (cond, 11, 'bold'), 'head': (cond, 10, 'bold'),
            'brand': (xcond, 18, xw, 'italic'), 'sec': (xcond, 16, xw, 'italic'), 'opt': (xcond, 12, xw, 'italic'),
            'pri': (xcond, 12, xw, 'italic'), 'pick': (xcond, 12, xw, 'italic'), 'hero': (xcond, 30, xw, 'italic'),
            'tile': (cond, 18, 'bold'),
        }

    def _style(self):
        st = ttk.Style(self)
        st.theme_use('clam')
        flat = {'lightcolor': P['pit'], 'darkcolor': P['pit']}
        st.configure('.', background=P['pit'], foreground=P['chrome'], fieldbackground=P['asphalt'],
                     bordercolor=P['line'], troughcolor=P['pit'], focuscolor=P['gold'], selectbackground=P['raised'],
                     selectforeground=P['chrome'], insertcolor=P['chrome'], font=self.f['text'], **flat)
        st.configure('Out.TButton', background=P['pit'], foreground=P['chrome'], bordercolor=P['edge'],
                     font=self.f['cond'], padding=(14, 5), relief='raised', **flat)
        st.map('Out.TButton', background=[('active', P['raised'])], bordercolor=[('active', P['muted'])],
               lightcolor=[('active', P['raised'])], darkcolor=[('active', P['raised'])],
               foreground=[('disabled', P['faint'])])
        st.configure('Top.TButton', background=P['top'], lightcolor=P['top'], darkcolor=P['top'],
                     foreground=P['chrome'], bordercolor=P['edge'], font=self.f['cond'], padding=(12, 3), relief='raised')
        st.map('Top.TButton', bordercolor=[('active', P['muted'])], background=[('active', P['top'])])
        red = {'background': P['red'], 'bordercolor': P['red'], 'lightcolor': P['red'], 'darkcolor': P['red']}
        st.configure('Pri.TButton', foreground='#FFFFFF', font=self.f['pri'], padding=(20, 6), relief='flat', **red)
        st.map('Pri.TButton',
               background=[('disabled', P['red_off']), ('active', P['red_dark'])],
               bordercolor=[('disabled', P['red_off']), ('active', P['red_dark'])],
               lightcolor=[('disabled', P['red_off']), ('active', P['red_dark'])],
               darkcolor=[('disabled', P['red_off']), ('active', P['red_dark'])],
               foreground=[('disabled', P['muted'])])
        st.configure('TCheckbutton', background=P['pit'], foreground=P['chrome'], indicatorbackground=P['asphalt'],
                     indicatorforeground='#FFFFFF', upperbordercolor=P['line'], lowerbordercolor=P['line'],
                     font=self.f['text'], padding=(2, 4))
        st.map('TCheckbutton', background=[('active', P['pit'])],
               indicatorbackground=[('selected', P['red']), ('active', P['raised'])])
        st.configure('TCombobox', fieldbackground=P['asphalt'], background=P['raised'], foreground=P['chrome'],
                     arrowcolor=P['chrome'], bordercolor=P['line'], padding=(8, 5), **flat)
        st.map('TCombobox', fieldbackground=[('readonly', P['asphalt'])], foreground=[('readonly', P['chrome'])],
               selectbackground=[('readonly', P['asphalt'])], selectforeground=[('readonly', P['chrome'])],
               bordercolor=[('focus', P['muted'])], background=[('active', P['line'])])
        self.option_add('*TCombobox*Listbox.background', P['pit'])
        self.option_add('*TCombobox*Listbox.foreground', P['chrome'])
        self.option_add('*TCombobox*Listbox.selectBackground', P['red'])
        self.option_add('*TCombobox*Listbox.selectForeground', '#FFFFFF')
        self.option_add('*TCombobox*Listbox.font', self.f['text'])
        st.configure('Treeview', background=P['row'], fieldbackground=P['row'], foreground=P['chrome'],
                     bordercolor=P['pit'], rowheight=26, font=self.f['text'], **flat)
        st.map('Treeview', background=[('selected', P['raised'])], foreground=[('selected', P['chrome'])])
        st.configure('Treeview.Heading', background=P['top'], foreground=P['muted'], bordercolor=P['top'],
                     lightcolor=P['top'], darkcolor=P['top'], relief='flat', font=self.f['head'], padding=(6, 6))
        st.map('Treeview.Heading', background=[('active', P['raised'])])
        for orient in ('Vertical', 'Horizontal'):
            st.configure('%s.TScrollbar' % orient, background=P['raised'], troughcolor=P['pit'],
                         bordercolor=P['pit'], arrowcolor=P['muted'], lightcolor=P['raised'], darkcolor=P['raised'],
                         gripcount=0)
            st.map('%s.TScrollbar' % orient, background=[('active', P['line'])])

    def _label(self, parent, text='', font='text', fg='chrome', bg='pit', **kw):
        return tk.Label(parent, text=text, font=self.f[font], fg=P[fg], bg=P[bg], **kw)

    def _sec(self, parent, text, bg='pit'):
        """Panel heading: red // and the title in condensed italic capitals."""
        row = tk.Frame(parent, bg=P[bg])
        self._label(row, '//', 'sec', 'red', bg).pack(side='left')
        self._label(row, ' ' + text.upper(), 'sec', 'chrome', bg).pack(side='left')
        return row

    def _panel(self, parent, **pack):
        frame = tk.Frame(parent, bg=P['pit'], padx=18, pady=14)
        frame.pack(fill='x', **pack)
        return frame

    # ------------------------------------------------------------- layout
    def _build(self):
        self._build_top()
        body = tk.Frame(self, bg=P['asphalt'], padx=24, pady=20)
        body.pack(fill='both', expand=True)
        side = tk.Frame(body, bg=P['pit'], width=300, padx=14, pady=14)
        side.pack(side='left', fill='y')
        side.pack_propagate(False)
        main = tk.Frame(body, bg=P['asphalt'])
        main.pack(side='left', fill='both', expand=True, padx=(20, 0))
        self._build_side(side)
        self._build_main(main)

    def _build_top(self):
        top = tk.Frame(self, bg=P['top'], padx=24, pady=10)
        top.pack(fill='x')
        slash = tk.Canvas(top, width=30, height=28, bg=P['top'], highlightthickness=0)
        slash.create_polygon(9, 1, 17, 1, 9, 27, 1, 27, fill=P['red'], outline='')
        slash.create_polygon(20, 1, 28, 1, 20, 27, 12, 27, fill=P['green'], outline='')
        slash.pack(side='left')
        self._label(top, 'DM', 'brand', 'chrome', 'top').pack(side='left', padx=(10, 0))
        self._label(top, ' SAVE UPDATE', 'brand', 'red', 'top').pack(side='left')
        self._label(top, 'v%s' % __version__, 'small', 'faint', 'top').pack(side='left', padx=10, pady=(6, 0))
        ttk.Button(top, text='RELOAD', style='Top.TButton', command=self.refresh_lists).pack(side='right')
        self.top_info = self._label(top, '', 'small', 'muted', 'top', anchor='e')
        self.top_info.pack(side='right', padx=14)
        chq = tk.Canvas(self, height=8, bg=P['asphalt'], highlightthickness=0)
        chq.pack(fill='x')

        def draw(event):
            chq.delete('all')
            for i in range(0, event.width // 8 + 1):
                if i % 2 == 0:
                    chq.create_rectangle(i * 8, 0, i * 8 + 8, 8, fill=P['chrome'], outline='')
        chq.bind('<Configure>', draw)

    def _build_side(self, side):
        # folders at the bottom, the save list fills the rest
        folders = tk.Frame(side, bg=P['pit'])
        folders.pack(side='bottom', fill='x', pady=(12, 0))
        self._sec(folders, 'Folders').pack(anchor='w', pady=(0, 6))
        for caption, var in (('SAVE FOLDER (SAUVEGARDES)', self.saves_dir),
                             ('WORKSHOP FOLDER (CONTENT\\%s)' % core.APP_ID, self.workshop_dir)):
            self._label(folders, caption, 'cap', 'muted').pack(anchor='w', pady=(6, 2))
            row = tk.Frame(folders, bg=P['pit'])
            row.pack(fill='x')
            tk.Entry(row, textvariable=var, font=self.f['small'], bg=P['asphalt'], fg=P['chrome'],
                     insertbackground=P['chrome'], relief='flat', highlightthickness=1,
                     highlightbackground=P['line'], highlightcolor=P['gold']).pack(side='left', fill='x',
                                                                                    expand=True, ipady=5)
            ttk.Button(row, text='…', width=3, style='Out.TButton',
                       command=lambda v=var: self.browse(v)).pack(side='left', padx=(4, 0))

        self._sec(side, 'Saves').pack(anchor='w', pady=(0, 8))
        wrap = tk.Frame(side, bg=P['pit'])
        wrap.pack(fill='both', expand=True)
        self.save_canvas = tk.Canvas(wrap, bg=P['pit'], highlightthickness=0, width=260)
        ysb = ttk.Scrollbar(wrap, orient='vertical', command=self.save_canvas.yview)
        self.save_canvas.configure(yscrollcommand=ysb.set)
        self.save_canvas.pack(side='left', fill='both', expand=True)
        ysb.pack(side='right', fill='y')
        self.save_list = tk.Frame(self.save_canvas, bg=P['pit'])
        win = self.save_canvas.create_window(0, 0, window=self.save_list, anchor='nw')
        self.save_list.bind('<Configure>', lambda e: self.save_canvas.configure(
            scrollregion=self.save_canvas.bbox('all')))
        self.save_canvas.bind('<Configure>', lambda e: self.save_canvas.itemconfigure(win, width=e.width))

        def wheel(event):
            self.save_canvas.yview_scroll(-1 if event.delta > 0 else 1, 'units')
        wrap.bind('<Enter>', lambda e: self.bind_all('<MouseWheel>', wheel))
        wrap.bind('<Leave>', lambda e: self.unbind_all('<MouseWheel>'))
        self.save_rows = []

    def _build_main(self, main):
        # hero: the chosen save in the team-colour style of Save Card
        self.hero = tk.Canvas(main, height=116, bg=P['red'], highlightthickness=0)
        self.hero.pack(fill='x')
        self.hero.bind('<Configure>', lambda e: self.draw_hero())

        mod = self._panel(main, pady=(16, 0))
        head = tk.Frame(mod, bg=P['pit'])
        head.pack(fill='x', pady=(0, 8))
        self._sec(head, 'Mod').pack(side='left')
        self._label(head, 'NEW VERSION', 'cap', 'muted').pack(side='left', padx=10, pady=(6, 0))
        row = tk.Frame(mod, bg=P['pit'])
        row.pack(fill='x')
        self.mod_box = ttk.Combobox(row, state='readonly', font=self.f['text'])
        self.mod_box.pack(side='left', fill='x', expand=True)
        self.mod_box.bind('<<ComboboxSelected>>', lambda e: self._remember_choice('mod'))
        ttk.Button(row, text='OTHER MOD FILE…', style='Out.TButton', command=self.pick_mod_file).pack(
            side='left', padx=(8, 0))

        bar = tk.Frame(mod, bg=P['pit'])
        bar.pack(fill='x', pady=(14, 0))
        self._label(bar, 'OPTIONS', 'opt', 'red').pack(side='left', padx=(0, 12))
        ttk.Checkbutton(bar, text='Overwrite era-vote rules', variable=self.overwrite_era).pack(side='left')
        ttk.Checkbutton(bar, text='Overwrite major-regulation values', variable=self.overwrite_major).pack(
            side='left', padx=(14, 0))
        self.apply_btn = ttk.Button(bar, text='APPLY UPDATE', style='Pri.TButton', command=self.run_apply,
                                    state='disabled')
        self.apply_btn.pack(side='right')
        ttk.Button(bar, text='SHOW CHANGES', style='Out.TButton', command=self.run_compare).pack(side='right',
                                                                                              padx=8)

        notes = tk.Frame(main, bg=P['row'])
        notes.pack(fill='x', pady=(16, 0))
        tk.Frame(notes, bg=P['red'], width=3).pack(side='left', fill='y')
        self.note_box = tk.Text(notes, height=2, wrap='word', relief='flat', bg=P['row'], fg=P['chrome'],
                                font=self.f['small'], padx=12, pady=8, highlightthickness=0, borderwidth=0,
                                insertbackground=P['chrome'])
        self.note_box.pack(side='left', fill='x', expand=True)
        self.note_box.insert('end', 'Pick a save on the left and a mod above, then press SHOW CHANGES. '
                                    'Nothing is written until you press APPLY UPDATE.')

        table = tk.Frame(main, bg=P['pit'], padx=18, pady=14)
        table.pack(fill='both', expand=True, pady=(16, 0))
        head = tk.Frame(table, bg=P['pit'])
        head.pack(fill='x', pady=(0, 8))
        self._sec(head, 'Changes').pack(side='left')
        legend = tk.Frame(head, bg=P['pit'])
        legend.pack(side='right')
        ttk.Checkbutton(legend, text='Show kept and skipped', variable=self.show_kept,
                        command=self.fill_tree).pack(side='left', padx=(0, 6))
        for text, colour in (('UPDATE', 'chrome'), ('KEPT', 'gold'), ('SKIPPED', 'faint')):
            tk.Frame(legend, bg=P[colour], width=10, height=10).pack(side='left', padx=(12, 5))
            self._label(legend, text, 'cap', 'muted').pack(side='left')
        cols = ('category', 'section', 'item', 'field', 'save', 'mod', 'action')
        frame = tk.Frame(table, bg=P['pit'])
        frame.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(frame, columns=cols, show='headings')
        widths = (100, 80, 150, 190, 130, 130, 130)
        for c, w in zip(cols, widths):
            self.tree.heading(c, text=(c + ' value' if c in ('save', 'mod') else c).upper(), anchor='w')
            self.tree.column(c, width=w, stretch=c in ('item', 'field', 'save', 'mod'))
        ysb = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        ysb.pack(side='right', fill='y')
        self.tree.tag_configure('update', foreground=P['chrome'])
        self.tree.tag_configure('keep', foreground=P['gold'])
        self.tree.tag_configure('skip', foreground=P['faint'])
        self.tree.tag_configure('odd', background=P['row2'])

        foot = tk.Frame(main, bg=P['asphalt'])
        foot.pack(fill='x', pady=(12, 0))
        ttk.Button(foot, text='RESTORE BACKUP…', style='Out.TButton', command=self.open_restore).pack(side='left')
        ttk.Button(foot, text='SAVE REPORT…', style='Out.TButton', command=self.save_report).pack(side='left',
                                                                                              padx=8)
        self._label(foot, 'Close Delta Manager (or go back to its main menu) before you apply or restore. '
                          'A backup is made in the save folder first.', 'small', 'muted', 'asphalt',
                    wraplength=520, justify='left').pack(side='left', padx=8)
        self._label(main, textvariable=self.status, font='small', fg='faint', bg='asphalt', anchor='w').pack(
            fill='x', pady=(8, 0))

    # ------------------------------------------------------------- save list and hero
    def _fill_save_list(self):
        for w in self.save_list.winfo_children():
            w.destroy()
        self.save_rows = []
        if not self.saves:
            self._label(self.save_list, 'No saves found. Check the save folder below.', 'small', 'muted',
                        wraplength=240, justify='left').pack(anchor='w', pady=8)
        mode = None
        for i, s in enumerate(self.saves):
            if s['mode'] != mode:
                mode = s['mode']
                self._label(self.save_list, MODE_NAMES.get(mode, mode.upper()), 'cap', 'muted').pack(
                    anchor='w', pady=(10 if i else 0, 4))
            row = tk.Frame(self.save_list, bg=P['row'], cursor='hand2')
            row.pack(fill='x', pady=(0, 2))
            bar = tk.Frame(row, bg=P['faint'], width=5)
            bar.pack(side='left', fill='y')
            edge = tk.Frame(row, bg=P['row'], width=3)
            edge.pack(side='right', fill='y')
            txt = tk.Frame(row, bg=P['row'], padx=10, pady=7)
            txt.pack(side='left', fill='x', expand=True)
            name = self._label(txt, s.get('team') or s['label'], 'semi', 'chrome', 'row', anchor='w')
            name.pack(fill='x')
            meta = self._label(txt, '%s  ·  season %s  ·  week %s' % (s['slot'], s.get('season', '?'),
                                                                      s.get('week', '?')),
                               'small', 'muted', 'row', anchor='w')
            meta.pack(fill='x')
            parts = (row, txt, name, meta)
            self.save_rows.append({'parts': parts, 'edge': edge, 'name': name, 'bar': bar})
            for w in parts + (bar,):
                w.bind('<Button-1>', lambda e, idx=i: self.choose_save(idx))
                w.bind('<Enter>', lambda e, idx=i: self._hover(idx, True))
                w.bind('<Leave>', lambda e, idx=i: self._hover(idx, False))
        self.save_canvas.yview_moveto(0)

    def _paint_row(self, idx, hover=False):
        r = self.save_rows[idx]
        on = idx == self.sel['save']
        bg = P['raised'] if (on or hover) else P['row']
        for w in r['parts']:
            w.configure(bg=bg)
        r['edge'].configure(bg=P['red'] if on else bg)
        r['bar'].configure(bg=P['red'] if on else P['faint'])
        team = self.saves[idx].get('team') or self.saves[idx]['label']
        r['name'].configure(text=team.upper() if on else team, font=self.f['pick' if on else 'semi'])

    def _hover(self, idx, inside):
        if idx < len(self.save_rows):
            self._paint_row(idx, inside)

    def choose_save(self, idx):
        old = self.sel['save']
        self.sel['save'] = idx
        for i in {old, idx}:
            if 0 <= i < len(self.save_rows):
                self._paint_row(i)
        if old != idx:
            self.counts = None
        self.draw_hero()

    def draw_hero(self):
        c = self.hero
        c.delete('all')
        w, h = max(c.winfo_width(), 400), int(c['height'])
        c.create_polygon(w * .58, 0, w * .74, 0, w * .74 - h * .47, h, w * .58 - h * .47, h,
                         fill=P['red_shade'], outline='')
        si = self.sel['save']
        if 0 <= si < len(self.saves):
            s = self.saves[si]
            kick = '%s  ·  %s  ·  SEASON %s  ·  WEEK %s' % (MODE_NAMES.get(s['mode'], s['mode'].upper()),
                                                           s['slot'].upper(), s.get('season', '?'),
                                                           s.get('week', '?'))
            title = (s.get('team') or s['label']).upper()
        else:
            kick, title = 'NO SAVE CHOSEN', 'PICK A SAVE'
        mi = self._entry_index(self.mod_box, self.mods, self.sel['mod']) if self.mods else -1
        sub = ('Mod: ' + self.mods[mi]['label']) if 0 <= mi < len(self.mods) else 'No mod chosen'
        c.create_text(26, 18, text=kick, anchor='nw', fill='#FFFFFF', font=self.f['cap'])
        c.create_text(24, 32, text=title, anchor='nw', fill='#FFFFFF', font=self.f['hero'])
        c.create_text(26, h - 12, text=sub, anchor='sw', fill='#FBE3DF', font=self.f['small'])
        counts = self.counts or {}
        tiles = (('UPDATES', counts.get('update')), ('KEPT', counts.get('keep')), ('SKIPPED', counts.get('skip')))
        tw, gap, x = 96, 2, w - 24
        for label, value in reversed(tiles):
            x0 = x - tw
            c.create_rectangle(x0, h - 82, x, h - 22, fill=P['red_tile'], outline='')
            c.create_text((x0 + x) / 2, h - 66, text='–' if value is None else str(value), fill='#FFFFFF',
                          font=self.f['tile'])
            c.create_text((x0 + x) / 2, h - 36, text=label, fill='#FFFFFF', font=self.f['cap'])
            x = x0 - gap

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
        self.draw_hero()

    def _select_entry(self, which, box, index):
        self.sel[which] = index
        if index >= 0:
            box.current(index)
        else:
            box.set('')

    def _remember_choice(self, which):
        if which == 'mod':
            self.sel['mod'] = self._entry_index(self.mod_box, self.mods, self.sel['mod'])
            self.counts = None
            self.draw_hero()

    @staticmethod
    def _entry_index(box, items, fallback):
        text = box.get()
        for i, item in enumerate(items):
            if item['label'] == text:
                return i
        i = box.current()
        return i if i >= 0 else fallback

    def refresh_lists(self):
        old = self.saves[self.sel['save']]['path'] if 0 <= self.sel['save'] < len(self.saves) else None
        self.saves = steam.list_saves(self.saves_dir.get())
        self._fill_save_list()
        keep = next((i for i, s in enumerate(self.saves) if s['path'] == old), 0)
        self.sel['save'] = -1
        self.counts = None
        if self.saves:
            self.choose_save(keep)
        self._fill_mod_list(select=0)
        self.top_info.configure(text='%d saves  ·  %d mods' % (len(self.saves), len(self.mods)))
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
        si = self.sel['save']
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
        self.counts = {'update': 0, 'keep': 0, 'skip': 0}
        for c in changes:
            self.counts[ACTION_TAGS.get(c.action, 'update')] += 1
        self.draw_hero()
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
        win = tk.Toplevel(self, bg=P['pit'], padx=18, pady=14)
        win.title('Restore backup - %s' % save_entry['label'])
        win.transient(self)
        dark_title_bar(win)
        self._sec(win, 'Restore backup').pack(anchor='w')
        self._label(win, 'Backups of this save, newest first. Restoring puts config.json, season.json and '
                         'meta.json back; the current files are backed up first.', 'small', 'muted',
                    wraplength=600, justify='left').pack(anchor='w', pady=(4, 10))
        lb = tk.Listbox(win, width=90, height=min(12, len(backups)), bg=P['row'], fg=P['chrome'],
                        selectbackground=P['red'], selectforeground='#FFFFFF', font=self.f['text'],
                        relief='flat', highlightthickness=0, borderwidth=0, activestyle='none')
        for folder, info in backups:
            lb.insert('end', '  %s   %s' % (os.path.basename(folder), info.get('mod') or ''))
        lb.selection_set(0)
        lb.pack(fill='both', expand=True)

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

        btns = tk.Frame(win, bg=P['pit'])
        btns.pack(fill='x', pady=(12, 0))
        ttk.Button(btns, text='RESTORE', style='Pri.TButton', command=do_restore).pack(side='right')
        ttk.Button(btns, text='CANCEL', style='Out.TButton', command=win.destroy).pack(side='right', padx=8)

    def fill_tree(self):
        self.tree.delete(*self.tree.get_children())
        n = 0
        for c in self.changes:
            tag = ACTION_TAGS.get(c.action, 'update')
            if tag != 'update' and not self.show_kept.get():
                continue
            tags = (tag, 'odd') if n % 2 else (tag,)
            n += 1
            self.tree.insert('', 'end', tags=tags, values=(
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
