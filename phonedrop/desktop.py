"""Native ttk UI. Imported only when the desktop starts, never by headless core tests."""
from __future__ import annotations

import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk
import qrcode

from core import PhoneDropServer, State, discover_lan_ips, lan_ipv4
from tls_support import create_tls_context
from version import APP_VERSION
from viewmodel import COLORS, change_executable_policy, dashboard, format_size, initial_geometry


class PhoneDropApp:
    def __init__(self, root, state: State, page: str, *, autostart=True):
        self.root, self.state, self.page = root, state, page
        self.server = self.worker = self.certificate_dir = None
        self.dialog = self.dialog_sid = self.settings = None
        self.fingerprint = ''
        self.qr_token = None
        self.photo = None
        self.closed = False
        self.layout = None
        self.after_id = None
        self.last_result = 'File hoàn tất sẽ xuất hiện ở đây.'
        self.received_count = 0
        self.addresses = discover_lan_ips() if autostart else []
        self.ip = self.addresses[0] if self.addresses else ''
        self.https = False
        self._style()
        root.title(f'PhoneDrop {APP_VERSION}')
        width, height = initial_geometry(root.winfo_screenwidth(), root.winfo_screenheight())
        root.geometry(f'{width}x{height}')
        root.minsize(min(600, width), min(450, height))
        root.configure(background=COLORS['background'])
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<Control-comma>', lambda event: self.open_settings())
        self._build()
        if autostart:
            self.start_server()
        self.refresh()

    def _style(self):
        c = COLORS
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', background=c['background'], foreground=c['text'], font=('Segoe UI', 10))
        style.configure('TFrame', background=c['background'])
        style.configure('Card.TFrame', background=c['panel'])
        style.configure('TLabel', background=c['background'], foreground=c['text'])
        style.configure('Card.TLabel', background=c['panel'])
        style.configure('Muted.TLabel', foreground=c['muted'])
        style.configure('CardMuted.TLabel', background=c['panel'], foreground=c['muted'])
        style.configure('Title.TLabel', font=('Segoe UI', 23, 'bold'))
        style.configure('Heading.TLabel', background=c['panel'], font=('Segoe UI', 13, 'bold'))
        style.configure('Safety.TLabel', foreground=c['warning'])
        style.configure('TButton', padding=(12, 9), background=c['border'], borderwidth=0,
                        foreground=c['text'], focuscolor=c['accent'])
        style.map('TButton', background=[('active', '#445977')], foreground=[('disabled', '#90a0b8')])
        style.configure('Accent.TButton', background=c['accent'], foreground=c['accent_text'])
        style.map('Accent.TButton', background=[('active', '#94ead6')], foreground=[('disabled', '#536f69')])
        style.configure('Danger.TButton', foreground=c['danger'])
        style.configure('TCheckbutton', padding=8, background=c['background'], foreground=c['text'])
        style.map('TCheckbutton', background=[('active', c['panel'])])
        style.configure('TEntry', fieldbackground=c['panel'], foreground=c['text'], insertcolor=c['text'])
        style.map('TEntry', fieldbackground=[('readonly', c['panel'])], foreground=[('readonly', c['text'])])
        style.configure('TCombobox', fieldbackground=c['panel'], foreground=c['text'], arrowcolor=c['text'])
        style.map('TCombobox', fieldbackground=[('readonly', c['panel'])], foreground=[('readonly', c['text'])])
        style.configure('Treeview', fieldbackground=c['panel'], background=c['panel'], foreground=c['text'],
                        rowheight=30, borderwidth=0)
        style.map('Treeview', background=[('selected', '#35596a')], foreground=[('selected', '#ffffff')])
        style.configure('Treeview.Heading', background=c['border'], foreground=c['text'], padding=8)
        style.configure('Horizontal.TProgressbar', background=c['accent'], troughcolor=c['border'], borderwidth=0)
        self.root.option_add('*TCombobox*Listbox.background', c['panel'])
        self.root.option_add('*TCombobox*Listbox.foreground', c['text'])

    def _build(self):
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        header = ttk.Frame(root, padding=(22, 14))
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text='PhoneDrop', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(header, text='Từ điện thoại đến máy tính của bạn', style='Muted.TLabel').grid(row=1, column=0, sticky='w')
        self.settings_button = ttk.Button(header, text='Cài đặt', command=self.open_settings)
        self.settings_button.grid(row=0, column=1, rowspan=2, padx=(12, 0))

        # Whole content scrolls when the screen or Windows text scaling leaves less space.
        viewport = ttk.Frame(root)
        viewport.grid(row=1, column=0, sticky='nsew', padx=(18, 10))
        viewport.rowconfigure(0, weight=1)
        viewport.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(viewport, highlightthickness=0, background=COLORS['background'])
        self.canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(viewport, orient='vertical', command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.body = ttk.Frame(self.canvas)
        self.window = self.canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.body.bind('<Configure>', lambda event: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', self._resize)
        root.bind('<MouseWheel>', self._wheel, add='+')
        root.bind('<Button-4>', lambda event: self.canvas.yview_scroll(-2, 'units'), add='+')
        root.bind('<Button-5>', lambda event: self.canvas.yview_scroll(2, 'units'), add='+')
        root.bind('<FocusIn>', self._reveal_focus, add='+')

        self.connect_card = ttk.Frame(self.body, style='Card.TFrame', padding=18)
        card = self.connect_card
        self.heading = ttk.Label(card, text='Sẵn sàng kết nối', style='Heading.TLabel', anchor='center')
        self.heading.pack(fill='x')
        self.qr_frame = tk.Frame(card, width=248, height=248, background=COLORS['panel'])
        self.qr_frame.pack(pady=12)
        self.qr_frame.pack_propagate(False)
        self.qr_label = tk.Label(self.qr_frame, background=COLORS['panel'], foreground=COLORS['accent'],
                                 font=('Segoe UI', 15, 'bold'), wraplength=220, justify='center')
        self.qr_label.pack(expand=True, fill='both')
        self.connection_detail = ttk.Label(card, style='CardMuted.TLabel', wraplength=275, justify='center', anchor='center')
        self.connection_detail.pack(fill='x', pady=(0, 12))
        self.action = ttk.Button(card, text='Tạo QR mới', command=self.connection_action)
        self.action.pack(fill='x')
        self.cert_button = ttk.Button(card, text='Đối chiếu chứng chỉ HTTPS', command=self.show_certificate)

        self.receive_card = ttk.Frame(self.body, style='Card.TFrame', padding=18)
        card = self.receive_card
        card.columnconfigure(0, weight=1)
        ttk.Label(card, text='Nhận file', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        self.transfer_name = ttk.Label(card, text='Chưa có file đang gửi', style='Card.TLabel', wraplength=460)
        self.transfer_name.grid(row=1, column=0, sticky='ew', pady=(18, 6))
        self.progress = ttk.Progressbar(card, mode='determinate', maximum=100)
        self.progress.grid(row=2, column=0, sticky='ew')
        self.transfer_amount = ttk.Label(card, text=self.last_result, style='CardMuted.TLabel', wraplength=460)
        self.transfer_amount.grid(row=3, column=0, sticky='ew', pady=(6, 20))
        self.history_title = ttk.Label(card, text='Đã nhận · 0 file', style='Heading.TLabel')
        self.history_title.grid(row=4, column=0, sticky='w', pady=(0, 10))
        history = ttk.Frame(card, style='Card.TFrame')
        history.grid(row=5, column=0, sticky='nsew')
        history.columnconfigure(0, weight=1)
        self.table = ttk.Treeview(history, columns=('name', 'size'), show='headings', height=5, selectmode='browse')
        self.table.heading('name', text='Tên file')
        self.table.heading('size', text='Dung lượng')
        self.table.column('name', width=280, minwidth=160)
        self.table.column('size', width=95, minwidth=85, anchor='e', stretch=False)
        self.table.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(history, orient='vertical', command=self.table.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.table.configure(yscrollcommand=scroll.set)
        hscroll = ttk.Scrollbar(history, orient='horizontal', command=self.table.xview)
        hscroll.grid(row=1, column=0, sticky='ew')
        self.table.configure(xscrollcommand=hscroll.set)
        ttk.Label(card, text='Thư mục nhận', style='CardMuted.TLabel').grid(row=6, column=0, sticky='w', pady=(14, 2))
        self.folder_label = ttk.Label(card, text=str(self.state.folder), style='Card.TLabel', wraplength=460)
        self.folder_label.grid(row=7, column=0, sticky='ew')
        ttk.Button(card, text='Mở thư mục', command=self.open_folder).grid(row=8, column=0, sticky='w', pady=(8, 0))

        footer = ttk.Frame(root, padding=(22, 10))
        footer.grid(row=2, column=0, sticky='ew')
        self.safety = ttk.Label(footer, style='Safety.TLabel', wraplength=850)
        self.safety.pack(anchor='w', fill='x')
        self.notice = ttk.Label(footer, text='Chỉ người được bạn cho phép mới gửi được file.', style='Muted.TLabel', wraplength=850)
        self.notice.pack(anchor='w', fill='x', pady=(3, 0))

    def _resize(self, event):
        width = max(280, event.width)
        self.canvas.itemconfigure(self.window, width=width)
        layout = 'wide' if width >= 800 else 'stacked'
        if layout != self.layout:
            self.layout = layout
            self.connect_card.grid_forget()
            self.receive_card.grid_forget()
            self.body.columnconfigure(0, weight=1 if layout == 'stacked' else 0)
            self.body.columnconfigure(1, weight=1 if layout == 'wide' else 0)
            self.connect_card.grid(row=0, column=0, sticky='new', padx=(0, 12 if layout == 'wide' else 0), pady=(0, 12))
            self.receive_card.grid(row=0 if layout == 'wide' else 1,
                                   column=1 if layout == 'wide' else 0, sticky='new', pady=(0, 12))
        wrap = max(220, width - (380 if layout == 'wide' else 60))
        for label in (self.transfer_name, self.transfer_amount, self.folder_label):
            label.configure(wraplength=wrap)
        self.safety.configure(wraplength=width - 12)
        self.notice.configure(wraplength=width - 12)

    def _wheel(self, event):
        if event.widget.winfo_toplevel() == self.root and not isinstance(event.widget, ttk.Treeview):
            self.canvas.yview_scroll(-int(event.delta / 120) or (-1 if event.delta > 0 else 1), 'units')

    def _reveal_focus(self, event):
        widget = event.widget
        if not str(widget).startswith(str(self.body) + '.'):
            return
        top = widget.winfo_rooty() - self.body.winfo_rooty()
        height = self.canvas.winfo_height()
        visible = self.canvas.canvasy(0)
        if top < visible or top + widget.winfo_height() > visible + height:
            self.canvas.yview_moveto(max(0, top - 25) / max(1, self.body.winfo_height()))

    def dismiss_dialog(self):
        if self.dialog is not None:
            self.dialog.destroy()
            self.dialog = self.dialog_sid = None

    def stop_server(self):
        server, self.server = self.server, None
        self.state.close()
        self.dismiss_dialog()
        if server is not None:
            server.shutdown()
            server.server_close()
            self.worker.join(timeout=2)
        if self.certificate_dir:
            self.certificate_dir.cleanup()
            self.certificate_dir = None
        self.fingerprint = ''
        self.qr_token = None

    def start_server(self):
        self.stop_server()
        if not lan_ipv4(self.ip):
            self.notice.configure(text='Không tìm thấy mạng nội bộ. Kết nối Wi-Fi/Ethernet rồi mở Cài đặt.')
            return
        try:
            tls_context = None
            if self.https:
                self.certificate_dir = tempfile.TemporaryDirectory(prefix='phonedrop-tls-')
                tls_context, self.fingerprint, _ = create_tls_context(self.ip, Path(self.certificate_dir.name))
            with self.state.lock:
                self.state.enabled = True
                self.state.rotate()
            self.server = PhoneDropServer((self.ip, 0), self.state, self.page, tls_context=tls_context)
            self.worker = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .1}, daemon=True)
            self.worker.start()
            self.notice.configure(text='Quét QR bằng camera điện thoại trên cùng mạng nội bộ.')
        except Exception:
            self.stop_server()
            self.notice.configure(text='Không thể mở kết nối. Kiểm tra IP và Firewall trong Cài đặt.')

    def connection_action(self):
        if self.server is None:
            self.start_server()
            if self.server is None:
                self.open_settings()
        else:
            self.state.rotate()
            self.dismiss_dialog()
            self.notice.configure(text='Đã đổi QR và thu hồi phiên cũ. File hoàn tất được giữ lại.')

    def open_folder(self):
        try:
            if os.name == 'nt':
                os.startfile(str(self.state.folder))
            else:
                subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(self.state.folder)])
        except OSError:
            messagebox.showerror('PhoneDrop', 'Không thể mở thư mục nhận.', parent=self.root)

    def _dialog_window(self, title):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.configure(background=COLORS['background'])
        dialog.geometry(f'{min(540, self.root.winfo_screenwidth()-60)}x{min(540, self.root.winfo_screenheight()-100)}')
        dialog.minsize(320, 300)
        return dialog

    def open_settings(self):
        if self.settings is not None:
            self.settings.lift()
            return
        dialog = self.settings = self._dialog_window('Cài đặt PhoneDrop')
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        canvas = tk.Canvas(dialog, background=COLORS['background'], highlightthickness=0)
        canvas.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(dialog, orient='vertical', command=canvas.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        canvas.configure(yscrollcommand=scroll.set)
        form = ttk.Frame(canvas, padding=20)
        window = canvas.create_window(0, 0, window=form, anchor='nw')
        form.columnconfigure(0, weight=1)
        def fit_settings(event):
            canvas.itemconfigure(window, width=event.width)
            for child in form.winfo_children():
                if isinstance(child, ttk.Label):
                    child.configure(wraplength=max(220, event.width - 42))
        canvas.bind('<Configure>', fit_settings)
        form.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        dialog.bind('<MouseWheel>', lambda event: canvas.yview_scroll(-int(event.delta / 120), 'units'))
        def reveal(event):
            if str(event.widget).startswith(str(form) + '.'):
                offset = event.widget.winfo_rooty() - form.winfo_rooty()
                if offset < canvas.canvasy(0) or offset + event.widget.winfo_height() > canvas.canvasy(0) + canvas.winfo_height():
                    canvas.yview_moveto(max(0, offset - 30) / max(1, form.winfo_height()))
        dialog.bind('<FocusIn>', reveal)
        ip = tk.StringVar(value=self.ip)
        https = tk.BooleanVar(value=self.https)
        dangerous = tk.BooleanVar(value=self.state.allow_executables)
        folder = tk.StringVar(value=str(self.state.folder))
        ttk.Label(form, text='Kết nối mạng', font=('Segoe UI', 13, 'bold')).grid(row=0, column=0, sticky='w')
        ttk.Label(form, text='IPv4 của máy tính trên Wi-Fi / Ethernet', style='Muted.TLabel').grid(row=1, column=0, sticky='w', pady=(12, 4))
        ip_box = ttk.Combobox(form, textvariable=ip, values=self.addresses)
        ip_box.grid(row=2, column=0, sticky='ew')
        ttk.Label(form, text='Có nhiều card mạng? Chọn IP mà điện thoại truy cập được.',
                  wraplength=440, style='Muted.TLabel').grid(row=3, column=0, sticky='ew', pady=(4, 12))
        ttk.Checkbutton(form, text='Dùng HTTPS với chứng chỉ tự ký', variable=https).grid(row=4, column=0, sticky='w')
        ttk.Label(form, text='Khi bật, đối chiếu fingerprint chứng chỉ với PC trước khi gửi. Trình duyệt sẽ cảnh báo chứng chỉ tự ký.',
                  wraplength=440, style='Muted.TLabel').grid(row=5, column=0, sticky='ew', pady=(0, 16))
        if self.fingerprint:
            ttk.Button(form, text='Xem fingerprint hiện tại', command=self.show_certificate).grid(row=6, column=0, sticky='w', pady=(0, 14))
        ttk.Label(form, text='Thư mục nhận', font=('Segoe UI', 13, 'bold')).grid(row=7, column=0, sticky='w')
        ttk.Entry(form, textvariable=folder, state='readonly').grid(row=8, column=0, sticky='ew', pady=8)
        def choose_folder():
            value = filedialog.askdirectory(parent=dialog, initialdir=folder.get(), mustexist=True)
            if value:
                folder.set(value)
        ttk.Button(form, text='Đổi thư mục', command=choose_folder).grid(row=9, column=0, sticky='w')
        ttk.Label(form, text='Bảo vệ file', font=('Segoe UI', 13, 'bold')).grid(row=10, column=0, sticky='w', pady=(20, 4))
        ttk.Checkbutton(form, text='Cho phép file thực thi - NGUY HIỂM', variable=dangerous).grid(row=11, column=0, sticky='w')
        ttk.Label(form, text='Mặc định chặn file thực thi. File khác vẫn có thể chứa nội dung gây hại; chỉ nhận từ người bạn tin cậy.',
                  wraplength=440, style='Muted.TLabel').grid(row=12, column=0, sticky='ew')
        ttk.Label(form, text='Áp dụng sẽ ngắt phiên hiện tại và tạo QR mới. File đang nhận chưa xong sẽ bị hủy.',
                  wraplength=440, style='Safety.TLabel').grid(row=13, column=0, sticky='ew', pady=(20, 4))
        def dismiss():
            dialog.destroy()
            self.settings = None
        def apply():
            new_ip = ip.get().strip()
            if not lan_ipv4(new_ip):
                messagebox.showerror('Kiểm tra địa chỉ IP', 'Nhập IPv4 mạng riêng của máy tính (10.x, 172.16–31.x hoặc 192.168.x).', parent=dialog)
                ip_box.focus_set()
                return
            try:
                destination = Path(folder.get()).resolve(strict=True)
                if not destination.is_dir():
                    raise OSError('Not a directory')
            except OSError:
                messagebox.showerror('Thư mục nhận', 'Không thể sử dụng thư mục đã chọn.', parent=dialog)
                return
            def confirm():
                return messagebox.askyesno('Cho phép file nguy hiểm?',
                    'File thực thi có thể gây hại khi mở. Chỉ bật nếu bạn hiểu rủi ro và tin cậy người gửi.\n\nTiếp tục?',
                    parent=dialog, icon='warning', default='no')
            allowed = change_executable_policy(self.state, dangerous.get(), confirm)
            if dangerous.get() and not allowed:
                dangerous.set(False)
                return
            try:
                self.state.set_folder(destination)
            except OSError:
                messagebox.showerror('Thư mục nhận', 'Không thể sử dụng thư mục đã chọn.', parent=dialog)
                return
            self.ip, self.https = new_ip, https.get()
            dismiss()
            self.start_server()
        buttons = ttk.Frame(dialog, padding=12)
        buttons.grid(row=1, column=0, columnspan=2, sticky='ew')
        ttk.Button(buttons, text='Hủy', command=dismiss).pack(side='left')
        ttk.Button(buttons, text='Áp dụng', style='Accent.TButton', command=apply).pack(side='right')
        dialog.protocol('WM_DELETE_WINDOW', dismiss)
        dialog.bind('<Escape>', lambda event: dismiss())
        ip_box.focus_set()

    def show_certificate(self):
        if not self.fingerprint:
            return
        dialog = self._dialog_window('Đối chiếu chứng chỉ HTTPS')
        dialog.geometry(f'{min(540, self.root.winfo_screenwidth()-60)}x340')
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Fingerprint SHA-256', font=('Segoe UI', 13, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='So sánh toàn bộ mã dưới đây với chứng chỉ trên điện thoại. Nếu khác, không gửi file.',
                  style='Muted.TLabel', wraplength=460).pack(anchor='w', pady=12)
        box = tk.Text(frame, height=4, width=36, wrap='char', font=('Consolas', 12),
                      background=COLORS['panel'], foreground=COLORS['text'], relief='flat', padx=10, pady=10)
        box.insert('1.0', self.fingerprint)
        box.configure(state='disabled')
        box.pack(fill='x', pady=8)
        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(self.fingerprint)
        ttk.Button(frame, text='Sao chép mã', command=copy).pack(side='left', pady=12)
        ttk.Button(frame, text='Đóng', command=dialog.destroy).pack(side='right', pady=12)
        dialog.bind('<Escape>', lambda event: dialog.destroy())

    def show_approval(self, session):
        self.dismiss_dialog()
        sid, ip, agent, _, _ = session
        dialog = self.dialog = self._dialog_window('Cho phép thiết bị gửi file?')
        self.dialog_sid = sid
        dialog.attributes('-topmost', True)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        viewport = ttk.Frame(dialog)
        viewport.grid(row=0, column=0, sticky='nsew')
        viewport.columnconfigure(0, weight=1)
        viewport.rowconfigure(0, weight=1)
        canvas = tk.Canvas(viewport, background=COLORS['background'], highlightthickness=0)
        canvas.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(viewport, command=canvas.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        canvas.configure(yscrollcommand=scroll.set)
        frame = ttk.Frame(canvas, padding=22)
        window = canvas.create_window(0, 0, window=frame, anchor='nw')
        title = ttk.Label(frame, text='Thiết bị muốn gửi file', font=('Segoe UI', 16, 'bold'))
        title.pack(anchor='w', fill='x')
        ttk.Label(frame, text=ip, font=('Segoe UI', 13)).pack(anchor='w', pady=(16, 8))
        agent_label = ttk.Label(frame, text=agent or 'Trình duyệt không cung cấp thông tin', style='Muted.TLabel')
        agent_label.pack(anchor='w', fill='x')
        warning = ttk.Label(frame, text='Chỉ cho phép nếu bạn vừa quét QR. IP và tên trình duyệt không chứng minh danh tính.', style='Muted.TLabel')
        warning.pack(anchor='w', fill='x', pady=(16, 0))
        def fit(event):
            canvas.itemconfigure(window, width=event.width)
            for label in (title, agent_label, warning):
                label.configure(wraplength=max(200, event.width - 48))
        canvas.bind('<Configure>', fit)
        frame.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        dialog.bind('<MouseWheel>', lambda event: canvas.yview_scroll(-int(event.delta / 120), 'units'))
        # Decision and deadline remain visible even when device information needs scrolling.
        footer = ttk.Frame(dialog, padding=(22, 12))
        footer.grid(row=1, column=0, sticky='ew')
        self.countdown = ttk.Label(footer, style='Safety.TLabel')
        self.countdown.pack(anchor='w', pady=(0, 12))
        buttons = ttk.Frame(footer)
        buttons.pack(fill='x')
        def decide(status):
            self.state.set_state(sid, status)
            self.dismiss_dialog()
        deny = ttk.Button(buttons, text='Từ chối', command=lambda: decide('denied'))
        deny.pack(side='left')
        allow = ttk.Button(buttons, text='Cho phép', style='Accent.TButton', command=lambda: decide('approved'))
        allow.pack(side='right')
        deny.bind('<Return>', lambda event: decide('denied'))
        allow.bind('<Return>', lambda event: decide('approved'))
        dialog.protocol('WM_DELETE_WINDOW', lambda: decide('denied'))
        dialog.bind('<Escape>', lambda event: decide('denied'))
        dialog.lift()
        deny.focus_set()

    def refresh(self):
        if self.closed:
            return
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        snapshot = self.state.snapshot()
        view = dashboard(snapshot, connected=self.server is not None)
        self.heading.configure(text=view['title'])
        self.connection_detail.configure(text=view['detail'])
        self.action.configure(text=view['action'], style='Danger.TButton' if snapshot['session'] else 'TButton')
        self.folder_label.configure(text=str(self.state.folder))
        if view['show_qr']:
            if snapshot['token'] != self.qr_token:
                qr = qrcode.QRCode(border=4, box_size=1)
                qr.add_data(self.server.origin + '/?t=' + snapshot['token'])
                qr.make(fit=True)
                qr.box_size = max(2, 240 // len(qr.get_matrix()))
                self.photo = ImageTk.PhotoImage(qr.make_image().get_image(), master=self.root)
                self.qr_label.configure(image=self.photo, text='')
                self.qr_token = snapshot['token']
        else:
            self.qr_token = None
            # All displayed states remain Vietnamese; no executable data appears in the QR area.
            text = {'offline':'Kết nối Wi-Fi\nhoặc Ethernet', 'pending':'Xác nhận thiết bị\ntrên máy tính',
                    'approved':'Đã cho phép\ngửi file', 'receiving':'Đang nhận\ntừ điện thoại'}[view['state']]
            self.qr_label.configure(image='', text=text)
        session = snapshot['session']
        if session and session[3] == 'pending':
            if self.dialog_sid != session[0]:
                self.show_approval(session)
            self.countdown.configure(text=f'Tự động từ chối sau {session[4]} giây.')
        else:
            self.dismiss_dialog()
        if self.fingerprint:
            if not self.cert_button.winfo_manager():
                self.cert_button.pack(fill='x', pady=(8, 0))
        else:
            self.cert_button.pack_forget()
        safety = ('HTTPS đang bật · Hãy đối chiếu chứng chỉ trước khi gửi.' if self.fingerprint else
                  'HTTP không mã hóa · Chỉ dùng mạng nội bộ mà bạn tin cậy.')
        if self.state.allow_executables:
            safety += ' Đang cho phép file thực thi.'
        self.safety.configure(text=safety)
        for _ in range(64):
            try:
                kind, data = self.state.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'received':
                self.received_count += 1
                self.table.insert('', 0, values=(data[0], format_size(data[1])))
                for item in self.table.get_children()[200:]:
                    self.table.delete(item)
                self.last_result = f'Đã lưu {data[0]} · {format_size(data[1])}'
                self.notice.configure(text='Đã nhận file. Bạn có thể mở thư mục để xem.')
            elif kind == 'cancelled':
                self.last_result = f'Đã hủy file chưa hoàn tất: {data}'
            elif kind == 'error':
                self.notice.configure(text=data)
        self.history_title.configure(text=f'Đã nhận · {self.received_count} file')
        self.transfer_name.configure(text=view['transfer'])
        self.progress.configure(value=view['progress'])
        self.transfer_amount.configure(text=view['amount'] or self.last_result)
        self.after_id = self.root.after(250, self.refresh)

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.stop_server()
        self.root.destroy()
