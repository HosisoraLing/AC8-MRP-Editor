"""Responsive desktop frontend, shared palette and layout for motion-graphics UI assets."""
from pathlib import Path
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

PALETTE = {'bg':'#080F1C', 'card':'#101C2D', 'input':'#0B1423', 'line':'#24364C',
           'text':'#EFF5FF', 'muted':'#9BAEC7', 'cyan':'#59E2E8', 'green':'#81E8B4', 'orange':'#FFB077'}

def app_directory():
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent

class ModernApp:
    def __init__(self, window, save_root, parse_save, set_mrp, SaveError):
        self.window = window
        self.parse_save = parse_save
        self.set_mrp = set_mrp
        self.SaveError = SaveError
        self.busy = False
        self.last_backup = None
        self.events = queue.Queue()
        self.backup_parent = app_directory() / 'Backups'
        self.scale = max(0.8, min(2.5, window.winfo_fpixels('1i') / 96.0))
        self.p = lambda value: max(1, round(value * self.scale))
        p = self.p
        self.c = PALETTE
        c = self.c
        window.title('ACE COMBAT 8 · MRP CONTROL')
        window.configure(bg=c['bg'])
        window.protocol('WM_DELETE_WINDOW', self.close)
        self.canvas = tk.Canvas(window, bg=c['bg'], highlightthickness=0, bd=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scroll = ttk.Scrollbar(window, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.body = tk.Frame(self.canvas, bg=c['bg'])
        self.body_id = self.canvas.create_window((0, 0), anchor='nw', window=self.body)
        self.body.bind('<Configure>', self.sync_scroll)
        self.canvas.bind('<Configure>', self.resize_body)
        self.canvas.bind_all('<MouseWheel>', self.mousewheel)
        self.frame = tk.Frame(self.body, bg=c['bg'])
        self.frame.pack(fill='both', expand=True, padx=p(28), pady=p(24))
        self.frame.columnconfigure(0, weight=1)
        self.normal_font = ('Microsoft YaHei UI', -p(14))

        header = tk.Frame(self.frame, bg=c['bg'])
        header.grid(row=0, column=0, sticky='ew', pady=(0,p(20)))
        header.columnconfigure(1, weight=1)
        mark = tk.Canvas(header, width=p(54), height=p(54), bg=c['bg'], highlightthickness=0)
        mark.grid(row=0, column=0, rowspan=2, padx=(0,p(16)))
        points = [(27,5),(32,24),(49,36),(49,42),(31,36),(29,45),(36,49),(36,52),(27,49),(18,52),(18,49),(25,45),(23,36),(5,42),(5,36),(22,24)]
        mark.create_polygon(*[p(v) for point in points for v in point], fill=c['cyan'])
        self.label(header, 'ACE COMBAT 8  /  MRP CONTROL', 11, fg=c['cyan'], font='Consolas').grid(row=0,column=1,sticky='w')
        self.label(header, '战役补给站', 29, bold=True).grid(row=1,column=1,sticky='w')
        self.label(header, 'WINDOWS · 存档编辑器', 11, fg=c['muted']).grid(row=1,column=2,sticky='e')

        metrics = self.card(self.frame)
        metrics.grid(row=1,column=0,sticky='ew',pady=(0,p(14)))
        metrics.columnconfigure(0,weight=1)
        self.label(metrics,'当前 MRP',13,fg=c['muted']).grid(row=0,column=0,sticky='w',padx=p(22),pady=(p(18),p(2)))
        self.current = tk.StringVar(value='读取中')
        self.current_number = tk.StringVar(value='—')
        self.label(metrics,self.current_number,38,bold=True,font='Bahnschrift').grid(row=1,column=0,sticky='w',padx=p(20))
        self.validation = tk.StringVar(value='正在读取存档')
        self.validation_label = self.label(metrics,self.validation,13,fg=c['green'])
        self.validation_label.grid(row=1,column=1,sticky='e',padx=p(22))
        self.label(metrics,'修改前自动备份全部存档，完成后回读验证。',12,fg=c['muted']).grid(row=2,column=0,columnspan=2,sticky='w',padx=p(22),pady=(p(6),p(18)))

        form = self.card(self.frame)
        form.grid(row=2,column=0,sticky='ew',pady=(0,p(16)))
        form.columnconfigure(0,weight=1)
        self.label(form,'01  存档位置',13,bold=True).grid(row=0,column=0,sticky='w',padx=p(22),pady=(p(20),p(10)))
        path_row = tk.Frame(form,bg=c['card'])
        path_row.grid(row=1,column=0,sticky='ew',padx=p(22))
        path_row.columnconfigure(0,weight=1)
        self.folder = tk.StringVar(value=str(save_root))
        self.folder_entry = self.entry(path_row,self.folder,13)
        self.folder_entry.grid(row=0,column=0,sticky='ew',ipady=p(10))
        self.browse_button = self.button(path_row,'选择目录',self.browse)
        self.browse_button.grid(row=0,column=1,padx=(p(10),0),sticky='ns')
        self.label(form,'选择包含 Campaign.sav 的 SaveGames 目录；默认自动定位。',11,fg=c['muted']).grid(row=2,column=0,sticky='w',padx=p(22),pady=(p(8),p(18)))
        separator=tk.Frame(form,bg=c['line'],height=p(1))
        separator.grid(row=3,column=0,sticky='ew',padx=p(22))
        amount_row=tk.Frame(form,bg=c['card'])
        amount_row.grid(row=4,column=0,sticky='ew',padx=p(22),pady=p(18))
        amount_row.columnconfigure(0,weight=1)
        self.label(amount_row,'02  目标 MRP',13,bold=True).grid(row=0,column=0,sticky='w',pady=(0,p(10)))
        self.amount=tk.StringVar(value='2000000')
        self.amount_entry=self.entry(amount_row,self.amount,28,font='Bahnschrift')
        self.amount_entry.grid(row=1,column=0,sticky='ew',ipady=p(10))
        preset=tk.Frame(amount_row,bg=c['card'])
        preset.grid(row=1,column=1,sticky='nsew',padx=(p(16),0))
        self.preset_button=self.button(preset,'200 万',lambda:self.amount.set('2000000'))
        self.preset_button.pack(fill='x',expand=True)
        self.label(amount_row,'输入整数，可用逗号分隔 · 范围 0–999,999,999',11,fg=c['muted']).grid(row=2,column=0,columnspan=2,sticky='w',pady=(p(8),0))

        actions=tk.Frame(self.frame,bg=c['bg'])
        actions.grid(row=3,column=0,sticky='ew',pady=(0,p(14)))
        actions.columnconfigure(0,weight=1)
        self.apply_button=self.button(actions,'备份并修改 MRP   →',self.apply,primary=True)
        self.apply_button.grid(row=0,column=0,sticky='ew',ipady=p(7))
        self.refresh_button=self.button(actions,'重新读取',self.refresh)
        self.refresh_button.grid(row=0,column=1,padx=(p(12),0),sticky='ns')
        self.backup_button=self.button(actions,'打开备份',self.open_backup)
        self.backup_button.grid(row=0,column=2,padx=(p(12),0),sticky='ns')
        self.backup_button.configure(state='disabled')

        status_card=self.card(self.frame)
        status_card.grid(row=4,column=0,sticky='ew')
        status_card.columnconfigure(0,weight=1)
        self.status_title=tk.StringVar(value='就绪 / READY')
        self.label(status_card,self.status_title,12,fg=c['cyan'],bold=True).grid(row=0,column=0,sticky='w',padx=p(20),pady=(p(15),p(6)))
        self.status=tk.StringVar(value='请先退出游戏，并等待 Steam 云同步完成。')
        self.status_label=self.label(status_card,self.status,12,fg=c['muted'])
        self.status_label.configure(wraplength=p(760),justify='left')
        self.status_label.grid(row=1,column=0,sticky='ew',padx=p(20),pady=(0,p(12)))
        self.progress=ttk.Progressbar(status_card,mode='indeterminate')
        self.progress.grid(row=2,column=0,sticky='ew',padx=p(20),pady=(0,p(12)))
        self.progress.grid_remove()
        self.label(self.frame,'自动备份  /  校验码重算  /  回读验证',11,fg=c['muted'],font='Microsoft YaHei UI').grid(row=5,column=0,sticky='w',pady=(p(14),0))
        self.controls=(self.folder_entry,self.amount_entry,self.browse_button,self.apply_button,self.refresh_button,self.preset_button)
        self.refresh()
        window.update_idletasks()
        wanted_w=max(p(900),self.body.winfo_reqwidth())
        wanted_h=self.body.winfo_reqheight()+p(50)
        usable_w=max(p(560),window.winfo_screenwidth()-p(70))
        usable_h=max(p(420),window.winfo_screenheight()-p(110))
        width=min(wanted_w,usable_w)
        height=min(wanted_h,usable_h)
        window.geometry(f'{width}x{height}')
        window.minsize(min(p(650),usable_w),min(p(440),usable_h))
        window.after(100,self.poll)

    def label(self,parent,text,size,fg=None,bold=False,font='Microsoft YaHei UI'):
        options={'bg':parent.cget('bg'),'fg':fg or self.c['text'],'font':(font,-self.p(size),'bold' if bold else 'normal'),'anchor':'w','bd':0}
        if isinstance(text,tk.StringVar):options['textvariable']=text
        else:options['text']=text
        return tk.Label(parent,**options)

    def card(self,parent):
        return tk.Frame(parent,bg=self.c['card'],highlightthickness=1,highlightbackground=self.c['line'],bd=0)

    def entry(self,parent,variable,size,font='Microsoft YaHei UI'):
        return tk.Entry(parent,textvariable=variable,bg=self.c['input'],fg=self.c['text'],insertbackground=self.c['cyan'],
                        selectbackground='#255565',selectforeground=self.c['text'],font=(font,-self.p(size)),bd=0,
                        highlightthickness=1,highlightbackground=self.c['line'],highlightcolor=self.c['cyan'],width=18,
                        disabledbackground=self.c['input'],disabledforeground=self.c['muted'])

    def button(self,parent,text,command,primary=False):
        bg=self.c['cyan'] if primary else self.c['card']
        fg=self.c['bg'] if primary else self.c['text']
        return tk.Button(parent,text=text,command=command,bg=bg,fg=fg,activebackground='#85F0F3' if primary else '#20364B',
                         activeforeground=fg,disabledforeground='#697E94',font=('Microsoft YaHei UI',-self.p(14),'bold' if primary else 'normal'),
                         relief='flat',bd=0,highlightthickness=0,padx=self.p(18),pady=self.p(11),cursor='hand2')

    def sync_scroll(self,event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        self.window.after_idle(self.update_scrollbar)

    def update_scrollbar(self):
        if self.body.winfo_reqheight()>self.canvas.winfo_height()+2:
            if not self.scroll.winfo_ismapped():self.scroll.pack(side='right',fill='y')
        elif self.scroll.winfo_ismapped():self.scroll.pack_forget()

    def resize_body(self,event):
        self.canvas.itemconfigure(self.body_id,width=event.width)
        self.status_label.configure(wraplength=max(self.p(320),event.width-self.p(100)))
        self.update_scrollbar()

    def mousewheel(self,event):
        if self.body.winfo_reqheight()>self.canvas.winfo_height():self.canvas.yview_scroll(-int(event.delta/120),'units')

    def refresh(self):
        try:
            info=self.parse_save((Path(self.folder.get())/'Campaign.sav').read_bytes())
            self.current_number.set(f'{info["value"]:,}')
            self.current.set(f'当前 MRP：{info["value"]:,} · 校验通过')
            self.validation.set('●  存档校验通过')
            self.validation_label.configure(fg=self.c['green'])
        except Exception as exc:
            self.current_number.set('—')
            self.current.set('无法读取：'+str(exc))
            self.validation.set('●  尚未载入')
            self.validation_label.configure(fg=self.c['orange'])
            self.status.set('无法读取战役存档：'+str(exc))

    def browse(self):
        selected=filedialog.askdirectory(initialdir=self.folder.get(),title='选择 SaveGames 目录',parent=self.window)
        if selected:self.folder.set(selected);self.refresh()

    def apply(self):
        try:
            text=self.amount.get().strip().replace(',','').replace('，','')
            if not(text.isascii() and text.isdecimal()):raise self.SaveError('请输入整数 MRP。')
            amount=int(text)
            if not 0<=amount<=999_999_999:raise self.SaveError('MRP 必须在 0～999,999,999 之间。')
            root=Path(self.folder.get())
        except Exception as exc:
            messagebox.showerror('无法修改',str(exc),parent=self.window);return
        self.busy=True
        for widget in self.controls:widget.configure(state='disabled')
        self.status_title.set('处理中 / WORKING')
        self.status.set('正在检查游戏进程和存档…')
        self.progress.grid();self.progress.start(14)
        def worker():
            try:
                result=self.set_mrp(root,amount,progress=lambda text:self.events.put(('progress',text)),backup_parent=self.backup_parent)
                self.events.put(('done',result))
            except Exception as exc:self.events.put(('error',str(exc)))
        threading.Thread(target=worker,daemon=False).start()

    def poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='progress':self.status.set(value);continue
                self.busy=False
                self.progress.stop();self.progress.grid_remove()
                for widget in self.controls:widget.configure(state='normal')
                self.refresh()
                if kind=='done':
                    self.last_backup=value['backup_directory']
                    self.backup_button.configure(state='normal')
                    self.status_title.set('修改完成 / VERIFIED')
                    self.status.set(f'{value["previous_MRP"]:,} → {value["current_MRP"]:,} MRP。回读和校验通过。\n备份：{self.last_backup}')
                else:
                    self.status_title.set('操作未完成 / ATTENTION')
                    self.status.set(value)
        except queue.Empty:pass
        self.window.after(100,self.poll)

    def open_backup(self):
        if self.last_backup:os.startfile(self.last_backup)

    def close(self):
        if self.busy:messagebox.showinfo('正在处理','正在备份或写入，请等待操作结束后关闭。',parent=self.window)
        else:self.window.destroy()
