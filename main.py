import sys, math, random, string
import qrcode
from PIL import Image, ImageDraw
from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence, QImage, QPixmap, QColor
from PySide6.QtWidgets import *

APP_NAME="QR Master Grid"
GRID_COLORS={"Subtle":"#30343b","Normal":"#555b66","Strong":"#8b93a1"}

DARK_STYLESHEET="""
QMainWindow{background:#17191d;} QWidget{font-family:"Segoe UI";font-size:13px;color:#e5e7eb;}
QFrame#sidebar,QFrame#previewPanel{background:#22252b;border:1px solid #353a43;border-radius:12px;}
QLabel#appTitle{font-size:26px;font-weight:700;color:#f8fafc;} QLabel#subtitle,QLabel#hint{color:#9ca3af;}
QLabel#sectionTitle{font-size:11px;font-weight:700;color:#9ca3af;}
QTextEdit{border:1px solid #3b404a;border-radius:8px;padding:8px;background:#181a1f;color:#f3f4f6;font-family:Consolas;}
QTextEdit:focus,QSpinBox:focus,QComboBox:focus{border:1px solid #3b82f6;}
QSpinBox,QComboBox{border:1px solid #3b404a;border-radius:7px;padding:5px 8px;min-width:72px;background:#181a1f;color:#f3f4f6;}
QPushButton{border:none;border-radius:8px;padding:7px 10px;background:transparent;color:#d1d5db;}
QPushButton:hover{background:#30353d;color:white;}
QToolButton{border:none;border-radius:9px;min-width:34px;min-height:34px;padding:0 10px;background:transparent;color:#d1d5db;font-weight:600;}
QToolButton:hover{background:#30353d;color:white;} QStatusBar{background:#17191d;color:#9ca3af;}
QScrollArea{border:none;background:#15171b;border-radius:8px;}
QPushButton#colorButton{border:1px solid #3b404a;background:#181a1f;text-align:left;padding:7px 10px;}
"""

class QRGrid:
    @staticmethod
    def matrix(text):
        qr=qrcode.QRCode(version=None,error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=1,border=0)
        qr.add_data(text); qr.make(fit=True); return qr.get_matrix()

class ClickablePreview(QLabel):
    moduleClicked=Signal(int,int)
    def __init__(self):
        super().__init__(); self.pix=None; self.zoom=1.; self.module=12
        self.stroke_cells=set()
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Your QR grid will appear here\n\nClick or drag across QR modules to recolor them")
        self.setStyleSheet("QLabel{color:#9ca3af;background:#15171b;border-radius:8px;padding:40px;}")
    def set_image(self,img,module):
        data=img.convert("RGBA").tobytes("raw","RGBA")
        qi=QImage(data,img.width,img.height,QImage.Format.Format_RGBA8888).copy()
        self.pix=QPixmap.fromImage(qi); self.module=module; self.refresh()
    def refresh(self):
        if not self.pix:return
        size=QSize(max(1,int(self.pix.width()*self.zoom)),max(1,int(self.pix.height()*self.zoom)))
        out=self.pix.scaled(size,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.FastTransformation)
        self.setPixmap(out); self.resize(out.size())
    def fit(self,size):
        if not self.pix:return
        self.zoom=min(max(100,size.width()-50)/self.pix.width(),max(100,size.height()-50)/self.pix.height(),1);self.refresh()
    def module_at(self,pos):
        if not self.pix:return None
        sx=int(pos.x()/self.zoom); sy=int(pos.y()/self.zoom)
        return sx//self.module, sy//self.module
    def paint_at(self,pos):
        cell=self.module_at(pos)
        if cell is None or cell in self.stroke_cells:return
        self.stroke_cells.add(cell); self.moduleClicked.emit(*cell)
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:
            self.stroke_cells.clear(); self.paint_at(e.position()); e.accept(); return
        super().mousePressEvent(e)
    def mouseMoveEvent(self,e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self.paint_at(e.position()); e.accept(); return
        super().mouseMoveEvent(e)
    def mouseReleaseEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:
            self.stroke_cells.clear(); e.accept(); return
        super().mouseReleaseEvent(e)

class Main(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(APP_NAME); self.resize(1320,850); self.setMinimumSize(1000,650)
        self.generated=None; self.matrices=[]; self.overrides=set()
        self.primary="#000000"; self.secondary="#ff0000"
        self.timer=QTimer(self); self.timer.setSingleShot(True); self.timer.setInterval(300); self.timer.timeout.connect(self.rebuild)
        self.build(); self.setStatusBar(QStatusBar()); self.statusBar().showMessage("Live preview — click or drag across QR modules to recolor them.")
    def build(self):
        c=QWidget(); self.setCentralWidget(c); root=QVBoxLayout(c); root.setContentsMargins(24,18,24,12); root.setSpacing(14)
        h=QHBoxLayout(); titles=QVBoxLayout(); t=QLabel(APP_NAME); t.setObjectName("appTitle"); sub=QLabel("Live QR editing on one shared module grid."); sub.setObjectName("subtitle"); titles.addWidget(t); titles.addWidget(sub); h.addLayout(titles); h.addStretch()
        self.theme=QToolButton(); self.theme.setText("☀"); self.theme.setToolTip("Light mode"); self.theme.clicked.connect(self.toggle_theme)
        save=QToolButton(); save.setText("Save"); save.clicked.connect(self.save)
        h.addWidget(self.theme); h.addWidget(save); root.addLayout(h)
        split=QSplitter(Qt.Orientation.Horizontal); split.addWidget(self.sidebar()); split.addWidget(self.preview_panel()); split.setSizes([390,900]); root.addWidget(split,1)
    def sidebar(self):
        f=QFrame(); f.setObjectName("sidebar"); l=QVBoxLayout(f); l.setContentsMargins(18,18,18,18); l.setSpacing(10)
        def section(x): q=QLabel(x); q.setObjectName("sectionTitle"); return q
        l.addWidget(section("QR CONTENT")); hint=QLabel("One text or URL per line."); hint.setObjectName("hint"); l.addWidget(hint)
        self.text=QTextEdit(); self.text.setPlaceholderText("Paste text or URLs here…"); self.text.textChanged.connect(self.changed); l.addWidget(self.text,1)
        r=QHBoxLayout(); rand=QPushButton("＋ Random"); rand.clicked.connect(self.random); clear=QPushButton("Clear"); clear.clicked.connect(self.text.clear); r.addWidget(rand); r.addStretch(); r.addWidget(clear); l.addLayout(r)
        l.addWidget(section("LAYOUT"))
        self.cols=self.spin(l,"Columns",1,30,1); self.module=self.spin(l,"Module size",2,100,15); self.border=self.spin(l,"Quiet zone",0,20,4)
        self.grid=QCheckBox("Show master grid"); self.grid.setChecked(True); self.grid.toggled.connect(self.changed); l.addWidget(self.grid)
        rr=QHBoxLayout(); rr.addWidget(QLabel("Grid visibility")); self.strength=QComboBox(); self.strength.addItems(GRID_COLORS); self.strength.setCurrentText("Normal"); self.strength.currentTextChanged.connect(self.changed); rr.addWidget(self.strength); l.addLayout(rr)
        l.addWidget(section("COLORS"))
        self.primary_btn=self.color_row(l,"Primary color",self.primary,True); self.secondary_btn=self.color_row(l,"Secondary color",self.secondary,False)
        info=QLabel("Click or hold L-click and drag across black QR modules to toggle them between Primary and Secondary. White cells are ignored."); info.setWordWrap(True); info.setObjectName("hint"); l.addWidget(info)
        return f
    def spin(self,l,name,a,b,v):
        r=QHBoxLayout(); r.addWidget(QLabel(name)); r.addStretch(); s=QSpinBox(); s.setRange(a,b); s.setValue(v); s.valueChanged.connect(self.changed); r.addWidget(s); l.addLayout(r); return s
    def color_row(self,l,label,color,is_primary):
        r=QHBoxLayout(); r.addWidget(QLabel(label)); r.addStretch(); b=QPushButton(); b.setObjectName("colorButton"); b.clicked.connect(lambda:self.pick_color(is_primary)); r.addWidget(b); l.addLayout(r); self.paint_color_button(b,color); return b
    def paint_color_button(self,b,color):
        b.setText(color.upper()); b.setIcon(self.color_icon(color))
    def color_icon(self,color):
        pix=QPixmap(18,18); pix.fill(QColor(color)); return pix
    def pick_color(self,is_primary):
        current=self.primary if is_primary else self.secondary
        color=QColorDialog.getColor(QColor(current),self,"Choose color")
        if not color.isValid(): return
        if is_primary:self.primary=color.name(); self.paint_color_button(self.primary_btn,self.primary)
        else:self.secondary=color.name(); self.paint_color_button(self.secondary_btn,self.secondary)
        self.repaint_image()
    def preview_panel(self):
        f=QFrame(); f.setObjectName("previewPanel"); l=QVBoxLayout(f); l.setContentsMargins(14,14,14,14)
        top=QHBoxLayout(); lab=QLabel("CLICK TO RECOLOR"); lab.setObjectName("sectionTitle"); top.addWidget(lab); top.addStretch()
        minus=QToolButton(); minus.setText("−"); minus.clicked.connect(lambda:self.zoom(.8)); self.z=QLabel("100%"); self.z.setMinimumWidth(45); self.z.setAlignment(Qt.AlignmentFlag.AlignCenter); plus=QToolButton(); plus.setText("+"); plus.clicked.connect(lambda:self.zoom(1.25)); fit=QPushButton("Fit"); fit.clicked.connect(self.fit)
        for w in (minus,self.z,plus,fit): top.addWidget(w)
        l.addLayout(top); self.scroll=QScrollArea(); self.scroll.setWidgetResizable(False); self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter); self.preview=ClickablePreview(); self.preview.moduleClicked.connect(self.toggle_module); self.scroll.setWidget(self.preview); l.addWidget(self.scroll,1); return f
    def values(self): return [x.strip() for x in self.text.toPlainText().splitlines() if x.strip()]
    def changed(self): self.overrides.clear(); self.timer.start()
    def random(self):
        vals=["https://example.com/"+''.join(random.choices(string.ascii_letters+string.digits,k=18)) for _ in range(6)]
        self.text.setPlainText((self.text.toPlainText().strip()+"\n" if self.text.toPlainText().strip() else "")+"\n".join(vals))
    def rebuild(self):
        vals=self.values()
        if not vals:self.generated=None; return
        try:self.matrices=[QRGrid.matrix(v) for v in vals]; self.make_image(); self.fit(); self.update_status()
        except Exception as e:self.statusBar().showMessage(f"Error: {e}")
    def geometry(self):
        cell=max(len(m)+2*self.border.value() for m in self.matrices); cols=self.cols.value(); rows=math.ceil(len(self.matrices)/cols); return cell,cols,rows
    def make_image(self):
        if not self.matrices:return
        cell,cols,rows=self.geometry(); mod=self.module.value(); W=cols*cell; H=rows*cell
        img=Image.new("RGB",(W*mod+1,H*mod+1),"white"); d=ImageDraw.Draw(img)
        if self.grid.isChecked():
            gc=GRID_COLORS[self.strength.currentText()]
            for x in range(0,W*mod+1,mod): d.line((x,0,x,H*mod),fill=gc)
            for y in range(0,H*mod+1,mod): d.line((0,y,W*mod,y),fill=gc)
        for i,m in enumerate(self.matrices):
            row,col=divmod(i,cols); off=(cell-len(m))//2; x0=col*cell+off; y0=row*cell+off
            for y,r in enumerate(m):
                for x,black in enumerate(r):
                    if black:
                        mx,my=x0+x,y0+y; color=self.secondary if (mx,my) in self.overrides else self.primary
                        d.rectangle((mx*mod,my*mod,mx*mod+mod,my*mod+mod),fill=color)
        self.generated=img; self.preview.set_image(img,mod)
    def pixel_counts(self):
        if not self.matrices:return 0,0
        primary=secondary=0; cell,cols,rows=self.geometry()
        for i,matrix in enumerate(self.matrices):
            row,col=divmod(i,cols); offset=(cell-len(matrix))//2; x0=col*cell+offset; y0=row*cell+offset
            for y,qr_row in enumerate(matrix):
                for x,black in enumerate(qr_row):
                    if black:
                        if (x0+x,y0+y) in self.overrides: secondary+=1
                        else: primary+=1
        return primary,secondary
    def update_status(self):
        primary,secondary=self.pixel_counts(); total=primary+secondary
        self.statusBar().showMessage(f"Remianing: {primary:,}  •  Done: {secondary:,}  •  Total: {total:,}")
    def repaint_image(self):
        if self.matrices:self.make_image(); self.preview.refresh(); self.update_status()
    def toggle_module(self,mx,my):
        if not self.is_black_module(mx,my):return
        key=(mx,my)
        if key in self.overrides:self.overrides.remove(key)
        else:self.overrides.add(key)
        self.repaint_image()
    def is_black_module(self,mx,my):
        cell,cols,rows=self.geometry()
        for i,m in enumerate(self.matrices):
            row,col=divmod(i,cols); off=(cell-len(m))//2; x0=col*cell+off; y0=row*cell+off
            x,y=mx-x0,my-y0
            if 0<=y<len(m) and 0<=x<len(m) and m[y][x]:return True
        return False
    def fit(self):
        if self.generated:self.preview.fit(self.scroll.viewport().size()); self.z.setText(f"{round(self.preview.zoom*100)}%")
    def zoom(self,f):
        if self.generated:self.preview.zoom=max(.02,min(self.preview.zoom*f,8)); self.preview.refresh(); self.z.setText(f"{round(self.preview.zoom*100)}%")
    def save(self):
        if not self.generated:return
        path,_=QFileDialog.getSaveFileName(self,"Save QR Master Grid","qr_master_grid.png","PNG Image (*.png)")
        if path:self.generated.save(path if path.lower().endswith(".png") else path+".png")
    def toggle_theme(self):
        app=QApplication.instance()
        if self.theme.text()=="☀":app.setStyleSheet(""); self.theme.setText("☾")
        else:app.setStyleSheet(DARK_STYLESHEET); self.theme.setText("☀")

def main():
    app=QApplication(sys.argv); app.setApplicationName(APP_NAME); app.setStyleSheet(DARK_STYLESHEET); w=Main(); w.show(); sys.exit(app.exec())
if __name__=="__main__":main()
