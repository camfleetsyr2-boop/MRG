import os
import sys
import json
import shutil
import tkinter as tk
from tkinter import messagebox, filedialog, ttk, colorchooser
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6, A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus import LongTable, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
import arabic_reshaper
from bidi.algorithm import get_display
import subprocess
from datetime import datetime, timedelta


# ============================================
# ثوابت الألوان والتصميم المحسّنة
# ============================================
class StyleConstants:
    # الألوان الأساسية
    PRIMARY_COLOR = "#2196F3"  # أزرق
    SUCCESS_COLOR = "#4CAF50"  # أخضر
    WARNING_COLOR = "#FF9800"  # برتقالي
    DANGER_COLOR = "#f44336"   # أحمر
    INFO_COLOR = "#00BCD4"     # سماوي
    PURPLE_COLOR = "#9C27B0"   # بنفسجي
    GREY_COLOR = "#607D8B"     # رمادي مزرق
    
    # ألوان الخلفيات
    BG_LIGHT = "#f5f5f5"
    BG_WHITE = "#ffffff"
    BG_BALANCE = "#e8f5e9"
    BG_EXCHANGE = "#fff3e0"
    BG_RECONCILE = "#fff9c4"
    
    # ألوان النصوص
    TEXT_DARK = "#212121"
    TEXT_LIGHT = "#757575"
    TEXT_SUCCESS = "#1b5e20"
    TEXT_WARNING = "#e65100"
    
    # الظلال والحدود
    SHADOW_COLOR = "#bdbdbd"
    BORDER_RADIUS = 3


def get_windows_font():
    windows_font_path = "C:/Windows/Fonts/arial.ttf"
    if os.path.exists(windows_font_path):
        return windows_font_path
    alternatives = [
        "C:/Windows/Fonts/times.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for alt in alternatives:
        if os.path.exists(alt):
            return alt
    return None


FONT_PATH = get_windows_font()


def reshape_text(text):
    if not text:
        return ""
    try:
        reshaped_text = arabic_reshaper.reshape(str(text))
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except:
        return str(text)


def make_arabic_paragraph(text, font_name, font_size, alignment='CENTER', line_height=1.2):
    """إنشاء فقرة نصية عربية منسقة لدعم النصوص الطويلة"""
    if not text:
        return ""
    
    # تشكيل النص العربي
    reshaped = reshape_text(text)
    
    # إنشاء نمط مخصص للفقرة
    style = ParagraphStyle(
        'ArabicParagraph',
        fontName=font_name,
        fontSize=font_size,
        leading=font_size * line_height,
        alignment=alignment,
        rightIndent=2,
        leftIndent=2,
        allowWidowWords=1,
        splitLongWords=True,
        wordWrap='RTL'
    )
    
    return Paragraph(reshaped, style)


def wrap_text(text, font_name, font_size, max_width, canvas_obj):
    if not text:
        return [""]
    text = str(text)
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        try:
            text_width = canvas_obj.stringWidth(reshape_text(test_line), font_name, font_size)
        except:
            text_width = 0
        if text_width <= max_width - 8:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines if lines else [""]


def draw_centered_cell(canvas_obj, x_center, y_bottom, cell_width, cell_height, text_lines, font_name, font_size, bg_color, text_color, line_height, align="center", vertical_padding=3):
    """رسم خلية مع نص متوسّط أفقياً وعمودياً"""
    # رسم الخلفية
    canvas_obj.setFillColor(bg_color)
    canvas_obj.rect(x_center - cell_width/2, y_bottom, cell_width, cell_height, fill=1, stroke=1)
    
    # حساب الارتفاع الكلي للنص
    total_text_height = len(text_lines) * line_height
    
    # حساب المساحة الفارغة وتوزيعها بالتساوي فوق وتحت النص
    available_space = cell_height - (vertical_padding * 2)
    y_start = y_bottom + vertical_padding + total_text_height
    
    canvas_obj.setFillColor(text_color)
    canvas_obj.setFont(font_name, font_size)
    
    # رسم كل سطر حسب المحاذاة المحددة
    for i, line in enumerate(text_lines):
        y_pos = y_start - (i * line_height)
        reshaped_line = reshape_text(line)
        if align == "right":
            # محاذاة لليمين
            text_width = canvas_obj.stringWidth(reshaped_line, font_name, font_size)
            x_pos = (x_center - cell_width/2) + cell_width - text_width - 3
            canvas_obj.drawString(x_pos, y_pos, reshaped_line)
        elif align == "left":
            # محاذاة لليسار
            x_pos = (x_center - cell_width/2) + 3
            canvas_obj.drawString(x_pos, y_pos, reshaped_line)
        else:
            # توسيط (الافتراضي)
            canvas_obj.drawCentredString(x_center, y_pos, reshaped_line)


def format_number(num):
    try:
        return f"{float(num):,.2f}"
    except:
        return "0.00"


def extract_number_from_text(text):
    try:
        cleaned = text
        for char in ['ل.س', 'ليرة سورية', 'دولار', 'يورو', '$', '€', ' ']:
            cleaned = cleaned.replace(char, "")
        cleaned = cleaned.replace(",", "")
        cleaned = ''.join(c for c in cleaned if c.isdigit() or c == '.' or c == '-')
        return float(cleaned)
    except:
        return 0.0


def hex_to_reportlab_color(hex_color):
    hex_color = hex_color.lstrip('#')
    return colors.Color(
        int(hex_color[0:2], 16) / 255.0,
        int(hex_color[2:4], 16) / 255.0,
        int(hex_color[4:6], 16) / 255.0
    )


class SarfApp:
    def __init__(self, root):
        self.root = root
        self.root.title("برنامج سند قبض/صرف/تصريف - النسخة النهائية V22")
        self.root.geometry("700x900")

        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.backup_dir = os.path.join(self.app_dir, "Backup")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.sarf_id_file = os.path.join(os.path.expanduser("~"), "sarf_app_last_sarf_id.txt")
        self.qabd_id_file = os.path.join(os.path.expanduser("~"), "sarf_app_last_qabd_id.txt")
        self.tasreef_id_file = os.path.join(os.path.expanduser("~"), "sarf_app_last_tasreef_id.txt")
        self.records_file = os.path.join(os.path.expanduser("~"), "sarf_app_records.json")
        self.records = self.load_records()
        self.balance_file = os.path.join(os.path.expanduser("~"), "sarf_app_balance.json")
        self.opening_balance_file = os.path.join(os.path.expanduser("~"), "sarf_app_opening_balance.json")
        self.settings_file = os.path.join(os.path.expanduser("~"), "sarf_app_settings.json")

        self.default_settings = {
            "fonts": {
                "title_size": 18,
                "header_size": 11,
                "body_size": 9,
                "table_header_size": 9
            },
            "colors": {
                "table_header_bg": "#cfe2f3",
                "table_header_text": "#000000",
                "row_deleted_bg": "#ffcccc",
                "row_deleted_text": "#cc0000",
                "row_edited_bg": "#ccffcc",
                "row_edited_text": "#006600",
                "row_pending_bg": "#ffe6cc",
                "row_pending_text": "#cc6600",
                "row_reconciled_bg": "#e6ffe6",
                "row_reconciled_text": "#006600",
                "balance_box_bg": "#e8f5e9",
                "balance_box_text": "#1b5e20"
            },
            "table": {
                "row_height": 25,
                "cell_padding": 5,
                "border_width": 1,
                "line_spacing": 1.2,
                "vertical_padding": 3
            },
            "margins": {
                "top": 40,
                "bottom": 40,
                "left": 50,
                "right": 50
            },
            "daily_report": {
                "col_widths": [45, 60, 65, 90, 110, 125],
                "show_time": True,
                "text_align": "center",
                "header_align": "center"
            },
            "query_report": {
                "col_widths": [45, 55, 60, 75, 90, 95, 75],
                "show_time": True,
                "text_align": "center",
                "header_align": "center"
            }
        }

        self.settings = self.load_settings()

        self.default_sarf_id = 1000
        self.default_qabd_id = 1
        self.default_tasreef_id = 1
        self.default_balance = {
            "ل.س": 7198500.00,
            "$": 42129.00,
            "€": 0.00
        }
        self.balance = self.load_balance()
        self.opening_balance = self.check_new_day()

        # إعداد مظهر النافذة الرئيسية
        self.root.configure(bg=StyleConstants.BG_LIGHT)
        
        # إنشاء إطار رئيسي مع تحسينات التصميم
        main_frame = tk.Frame(self.root, padx=20, pady=15, bg=StyleConstants.BG_LIGHT)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # عنوان رئيسي محسّن
        title_label = tk.Label(
            main_frame, 
            text="📋 نظام إدارة سندات القبض والصرف والتصريف", 
            font=("Arial", 18, "bold"),
            bg=StyleConstants.BG_LIGHT,
            fg=StyleConstants.TEXT_DARK
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # إطار الرصيد المحسّن
        balance_frame = tk.Frame(
            main_frame, 
            bg=StyleConstants.BG_BALANCE, 
            padx=20, 
            pady=15, 
            relief=tk.RAISED, 
            borderwidth=2
        )
        balance_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")

        tk.Label(
            balance_frame, 
            text="💰 رصيد الصندوق الحالي", 
            font=("Arial", 15, "bold"), 
            bg=StyleConstants.BG_BALANCE, 
            fg=StyleConstants.TEXT_SUCCESS
        ).grid(row=0, column=0, columnspan=6, pady=(0, 10))

        tk.Label(balance_frame, text="ليرة سورية:", font=("Arial", 11, "bold"), bg=StyleConstants.BG_BALANCE, fg=StyleConstants.TEXT_DARK).grid(row=1, column=0, sticky="e", padx=5)
        self.balance_syp_var = tk.StringVar(value=format_number(self.balance["ل.س"]))
        tk.Label(balance_frame, textvariable=self.balance_syp_var, font=("Arial", 13, "bold"), bg=StyleConstants.BG_BALANCE, fg=StyleConstants.TEXT_SUCCESS, width=15, anchor="e").grid(row=1, column=1, padx=5)

        tk.Label(balance_frame, text="دولار:", font=("Arial", 11, "bold"), bg=StyleConstants.BG_BALANCE, fg=StyleConstants.TEXT_DARK).grid(row=1, column=2, sticky="e", padx=5)
        self.balance_usd_var = tk.StringVar(value=format_number(self.balance["$"]))
        tk.Label(balance_frame, textvariable=self.balance_usd_var, font=("Arial", 13, "bold"), bg=StyleConstants.BG_BALANCE, fg=StyleConstants.TEXT_SUCCESS, width=15, anchor="e").grid(row=1, column=3, padx=5)

        tk.Label(balance_frame, text="يورو:", font=("Arial", 11, "bold"), bg=StyleConstants.BG_BALANCE, fg=StyleConstants.TEXT_DARK).grid(row=1, column=4, sticky="e", padx=5)
        self.balance_eur_var = tk.StringVar(value=format_number(self.balance["€"]))
        tk.Label(balance_frame, textvariable=self.balance_eur_var, font=("Arial", 13, "bold"), bg=StyleConstants.BG_BALANCE, fg=StyleConstants.TEXT_SUCCESS, width=15, anchor="e").grid(row=1, column=5, padx=5)

        tk.Button(
            balance_frame, 
            text="⚙️ ضبط الرصيد", 
            command=self.manual_balance_adjust, 
            bg=StyleConstants.WARNING_COLOR, 
            fg="white", 
            font=("Arial", 10, "bold"),
            relief=tk.RAISED,
            cursor="hand2"
        ).grid(row=1, column=6, padx=10)

        # قسم نوع السند المحسّن
        type_label_frame = tk.LabelFrame(
            main_frame,
            text="📝 نوع السند",
            font=("Arial", 12, "bold"),
            bg=StyleConstants.BG_LIGHT,
            fg=StyleConstants.TEXT_DARK,
            padx=10,
            pady=10
        )
        type_label_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        
        self.order_type_var = tk.StringVar(value="صرف")
        type_frame = tk.Frame(type_label_frame, bg=StyleConstants.BG_LIGHT)
        type_frame.pack()

        tk.Radiobutton(
            type_frame, 
            text="💸 سند صرف", 
            variable=self.order_type_var, 
            value="صرف", 
            font=("Arial", 11),
            bg=StyleConstants.BG_LIGHT,
            activebackground=StyleConstants.BG_LIGHT,
            command=self.on_type_change
        ).pack(side=tk.RIGHT, padx=10)
        
        tk.Radiobutton(
            type_frame, 
            text="💵 سند قبض", 
            variable=self.order_type_var, 
            value="قبض", 
            font=("Arial", 11),
            bg=StyleConstants.BG_LIGHT,
            activebackground=StyleConstants.BG_LIGHT,
            command=self.on_type_change
        ).pack(side=tk.RIGHT, padx=10)
        
        tk.Radiobutton(
            type_frame, 
            text="💱 تصريف", 
            variable=self.order_type_var, 
            value="تصريف", 
            font=("Arial", 11),
            bg=StyleConstants.BG_LIGHT,
            activebackground=StyleConstants.BG_LIGHT,
            command=self.on_type_change
        ).pack(side=tk.RIGHT, padx=10)

        # إطار إدخال البيانات المحسّن
        data_frame = tk.LabelFrame(
            main_frame,
            text="📄 بيانات السند",
            font=("Arial", 12, "bold"),
            bg=StyleConstants.BG_LIGHT,
            fg=StyleConstants.TEXT_DARK,
            padx=15,
            pady=15
        )
        data_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky="ew")

        labels = [
            ("🔢 الرقم التسلسلي:", "id"),
            ("💰 المبلغ:", "amount"),
            ("✍️ المبلغ كتابة:", "amount_words"),
            ("👤 إلى أمين الصندوق:", "treasurer"),
            ("🧑‍💼 إلى السيد:", "payee"),
            ("📌 وذلك لقاء:", "reason")
        ]

        self.entries = {}
        self.currency_var = tk.StringVar(value="ل.س")

        for i, (label_text, key) in enumerate(labels):
            tk.Label(
                data_frame, 
                text=label_text, 
                font=("Arial", 11),
                bg=StyleConstants.BG_LIGHT,
                fg=StyleConstants.TEXT_DARK
            ).grid(row=i, column=1, sticky="e", pady=8, padx=5)
            
            if key == "amount":
                amount_frame = tk.Frame(data_frame, bg=StyleConstants.BG_LIGHT)
                amount_frame.grid(row=i, column=0, pady=8, padx=5, sticky="e")
                
                self.entries["amount"] = tk.Entry(
                    amount_frame, 
                    font=("Arial", 12), 
                    width=20, 
                    justify="right",
                    bg=StyleConstants.BG_WHITE,
                    relief=tk.SUNKEN
                )
                self.entries["amount"].pack(side=tk.RIGHT)
                
                currency_menu = tk.OptionMenu(
                    amount_frame, 
                    self.currency_var, 
                    "ل.س", "$", "€"
                )
                currency_menu.config(
                    font=("Arial", 11), 
                    width=4,
                    bg=StyleConstants.PRIMARY_COLOR,
                    fg="white",
                    activebackground=StyleConstants.PRIMARY_COLOR
                )
                currency_menu.pack(side=tk.RIGHT, padx=5)
            else:
                entry = tk.Entry(
                    data_frame, 
                    font=("Arial", 11), 
                    width=35, 
                    justify="right",
                    bg=StyleConstants.BG_WHITE,
                    relief=tk.SUNKEN
                )
                entry.grid(row=i, column=0, pady=8, padx=5, sticky="w")
                self.entries[key] = entry

        self.entries["treasurer"].insert(0, "محمد الهواش")

        # إطار الترصيد المحسّن
        self.reconcile_var = tk.BooleanVar(value=False)
        reconcile_frame = tk.Frame(
            main_frame, 
            bg=StyleConstants.BG_RECONCILE, 
            padx=15, 
            pady=10,
            relief=tk.RAISED,
            borderwidth=1
        )
        reconcile_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        tk.Checkbutton(
            reconcile_frame, 
            text="✅ ترصيد (يؤثر على الصندوق - للتجميع في قائمة الترصيد للنقل الورقي)",
            variable=self.reconcile_var, 
            font=("Arial", 11, "bold"),
            bg=StyleConstants.BG_RECONCILE, 
            fg=StyleConstants.TEXT_WARNING,
            selectcolor=StyleConstants.BG_RECONCILE,
            activebackground=StyleConstants.BG_RECONCILE
        ).pack(side=tk.RIGHT, padx=10)

        # إطار التصريف المحسّن
        self.exchange_frame = tk.LabelFrame(
            main_frame,
            text="💱 بيانات التصريف",
            font=("Arial", 12, "bold"),
            bg=StyleConstants.BG_EXCHANGE,
            fg=StyleConstants.TEXT_WARNING,
            padx=15,
            pady=15
        )
        self.exchange_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")
        self.exchange_frame.grid_remove()

        tk.Label(self.exchange_frame, text="🔄 نوع العملية:", font=("Arial", 11), bg=StyleConstants.BG_EXCHANGE, fg=StyleConstants.TEXT_DARK).grid(row=0, column=0, sticky="e", pady=5)
        self.exchange_type_var = tk.StringVar(value="بيع")
        ex_type_frame = tk.Frame(self.exchange_frame, bg=StyleConstants.BG_EXCHANGE)
        ex_type_frame.grid(row=0, column=1, sticky="w")

        tk.Radiobutton(ex_type_frame, text="💰 بيع (دولار/يورو → ليرة)", variable=self.exchange_type_var, value="بيع", font=("Arial", 10), bg=StyleConstants.BG_EXCHANGE, command=self.calculate_exchange).pack(side=tk.RIGHT, padx=8)
        tk.Radiobutton(ex_type_frame, text="🛒 شراء (ليرة → دولار/يورو)", variable=self.exchange_type_var, value="شراء", font=("Arial", 10), bg=StyleConstants.BG_EXCHANGE, command=self.calculate_exchange).pack(side=tk.RIGHT, padx=8)
        tk.Radiobutton(ex_type_frame, text="💶 يورو → 💵 دولار", variable=self.exchange_type_var, value="يورو_دولار", font=("Arial", 10), bg=StyleConstants.BG_EXCHANGE, command=self.calculate_exchange).pack(side=tk.RIGHT, padx=8)
        tk.Radiobutton(ex_type_frame, text="💵 دولار → 💶 يورو", variable=self.exchange_type_var, value="دولار_يورو", font=("Arial", 10), bg=StyleConstants.BG_EXCHANGE, command=self.calculate_exchange).pack(side=tk.RIGHT, padx=8)

        tk.Label(self.exchange_frame, text="📈 سعر الصرف:", font=("Arial", 11), bg=StyleConstants.BG_EXCHANGE, fg=StyleConstants.TEXT_DARK).grid(row=1, column=0, sticky="e", pady=5)
        self.exchange_rate_var = tk.StringVar()
        tk.Entry(self.exchange_frame, font=("Arial", 12), width=15, textvariable=self.exchange_rate_var, justify="right", bg=StyleConstants.BG_WHITE).grid(row=1, column=1, sticky="w", pady=5)
        self.exchange_rate_var.trace_add("write", self.calculate_exchange)

        tk.Label(self.exchange_frame, text="💸 المبلغ المراد تصريفه:", font=("Arial", 11), bg=StyleConstants.BG_EXCHANGE, fg=StyleConstants.TEXT_DARK).grid(row=2, column=0, sticky="e", pady=5)
        self.exchange_amount_var = tk.StringVar()
        tk.Entry(self.exchange_frame, font=("Arial", 12), width=15, textvariable=self.exchange_amount_var, justify="right", bg=StyleConstants.BG_WHITE).grid(row=2, column=1, sticky="w", pady=5)
        self.exchange_amount_var.trace_add("write", self.calculate_exchange)

        tk.Label(self.exchange_frame, text="💵 المبلغ الناتج:", font=("Arial", 11, "bold"), bg=StyleConstants.BG_EXCHANGE, fg=StyleConstants.TEXT_DARK).grid(row=3, column=0, sticky="e", pady=5)
        self.exchange_result_var = tk.StringVar(value="0")
        tk.Label(self.exchange_frame, textvariable=self.exchange_result_var, font=("Arial", 13, "bold"), bg=StyleConstants.BG_EXCHANGE, fg=StyleConstants.SUCCESS_COLOR, width=15, anchor="e").grid(row=3, column=1, sticky="w", pady=5)

        # إطار تأثير التصريف المحسّن
        self.exchange_impact_frame = tk.Frame(
            main_frame, 
            bg=StyleConstants.BG_EXCHANGE, 
            padx=15, 
            pady=10, 
            relief=tk.RAISED, 
            borderwidth=1
        )
        self.exchange_impact_frame.grid(row=6, column=0, columnspan=2, pady=5, sticky="ew")
        self.exchange_impact_frame.grid_remove()

        tk.Label(
            self.exchange_impact_frame, 
            text="📊 تأثير التصريف على الصناديق:", 
            font=("Arial", 12, "bold"), 
            bg=StyleConstants.BG_EXCHANGE, 
            fg=StyleConstants.TEXT_WARNING
        ).grid(row=0, column=0, columnspan=4, pady=5)

        self.impact_syp_var = tk.StringVar(value="ل.س: 0.00")
        self.impact_usd_var = tk.StringVar(value="$: 0.00")
        self.impact_eur_var = tk.StringVar(value="€: 0.00")

        tk.Label(self.exchange_impact_frame, textvariable=self.impact_syp_var, font=("Arial", 11, "bold"), bg=StyleConstants.BG_EXCHANGE, fg=StyleConstants.TEXT_SUCCESS).grid(row=1, column=0, padx=10)
        tk.Label(self.exchange_impact_frame, textvariable=self.impact_usd_var, font=("Arial", 11, "bold"), bg=StyleConstants.BG_EXCHANGE, fg=StyleConstants.TEXT_SUCCESS).grid(row=1, column=1, padx=10)
        tk.Label(self.exchange_impact_frame, textvariable=self.impact_eur_var, font=("Arial", 11, "bold"), bg=StyleConstants.BG_EXCHANGE, fg=StyleConstants.TEXT_SUCCESS).grid(row=1, column=2, padx=10)

        self.order_type_var.trace_add("write", self.on_order_type_change)
        self.update_id_display()

        self.root.after(1000, self.check_pending_reconciliation)

        # إطار الأزرار المحسّن
        btn_frame = tk.LabelFrame(
            main_frame,
            text="🛠️ العمليات",
            font=("Arial", 13, "bold"),
            bg=StyleConstants.BG_LIGHT,
            fg=StyleConstants.TEXT_DARK,
            padx=15,
            pady=15
        )
        btn_frame.grid(row=7, column=0, columnspan=2, pady=20)

        # تعريف الأزرار مع أيقونات وألوان محسّنة
        buttons_config = [
            ("💾 حفظ كـ PDF", self.save_pdf, StyleConstants.SUCCESS_COLOR),
            ("🖨️ حفظ وطباعة", self.save_and_print, StyleConstants.PRIMARY_COLOR),
            ("✏️ تعديل سند", self.open_edit_window, "#FF5722"),
            ("🗑️ حذف سندات", self.open_delete_window, StyleConstants.DANGER_COLOR),
            ("✅ قائمة الترصيد", self.open_reconciliation_window, StyleConstants.PURPLE_COLOR),
            ("📊 تقرير اليوم", self.generate_daily_report, StyleConstants.WARNING_COLOR),
            ("⚖️ الموازنة", self.open_monthly_balance, StyleConstants.GREY_COLOR),
            ("🔍 استعلام", self.open_query_window, StyleConstants.INFO_COLOR),
            ("⚙️ الإعدادات", self.open_settings_window, "#9E9E9E"),
            ("📥 استرجاع نسخة", self.restore_backup, "#795548"),
            ("🔄 تصفير العداد", self.reset_id, "#f44336")
        ]

        for btn_text, btn_command, btn_bg in buttons_config:
            tk.Button(
                btn_frame, 
                text=btn_text, 
                command=btn_command, 
                bg=btn_bg, 
                fg="white", 
                font=("Arial", 11, "bold"),
                width=13,
                relief=tk.RAISED,
                cursor="hand2",
                activebackground=btn_bg,
                activeforeground="white"
            ).pack(side=tk.LEFT, padx=5, pady=5)

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    saved_settings = json.load(f)
                    settings = self.default_settings.copy()
                    for key, value in saved_settings.items():
                        if key in settings:
                            if isinstance(value, dict):
                                settings[key].update(value)
                            else:
                                settings[key] = value
                    return settings
            except:
                pass
        return self.default_settings.copy()

    def save_settings(self):
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل حفظ الإعدادات: {str(e)}")
            return False

    def open_settings_window(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("إعدادات البرنامج والتقارير")
        settings_win.geometry("800x700")
        settings_win.resizable(True, True)

        notebook = ttk.Notebook(settings_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        fonts_frame = tk.Frame(notebook, padx=20, pady=10)
        notebook.add(fonts_frame, text="الخطوط والأحجام")

        colors_frame = tk.Frame(notebook, padx=20, pady=10)
        notebook.add(colors_frame, text="الألوان")

        tables_frame = tk.Frame(notebook, padx=20, pady=10)
        notebook.add(tables_frame, text="الجداول")

        margins_frame = tk.Frame(notebook, padx=20, pady=10)
        notebook.add(margins_frame, text="الهوامش")

        tk.Label(fonts_frame, text="أحجام الخطوط", font=("Arial", 14, "bold")).pack(pady=10)

        fonts_grid = tk.Frame(fonts_frame)
        fonts_grid.pack(pady=10)

        font_settings = [
            ("حجم عنوان التقرير", "title_size", 18),
            ("حجم رأس الجدول", "table_header_size", 9),
            ("حجم نص الجسم", "body_size", 9),
            ("حجم المعلومات", "header_size", 11)
        ]

        self.font_vars = {}
        for i, (label, key, default) in enumerate(font_settings):
            tk.Label(fonts_grid, text=label, font=("Arial", 11)).grid(row=i, column=0, sticky="e", pady=5, padx=10)
            var = tk.IntVar(value=self.settings["fonts"].get(key, default))
            self.font_vars[key] = var
            tk.Spinbox(fonts_grid, from_=6, to=24, textvariable=var, width=10, font=("Arial", 11)).grid(row=i, column=1, pady=5, padx=10)

        tk.Label(colors_frame, text="ألوان التقارير", font=("Arial", 14, "bold")).pack(pady=10)

        colors_grid = tk.Frame(colors_frame)
        colors_grid.pack(pady=10)

        color_settings = [
            ("خلفية رأس الجدول", "table_header_bg"),
            ("نص رأس الجدول", "table_header_text"),
            ("خلفية صف محذوف", "row_deleted_bg"),
            ("نص صف محذوف", "row_deleted_text"),
            ("خلفية صف معدل", "row_edited_bg"),
            ("نص صف معدل", "row_edited_text"),
            ("خلفية بانتظار الترصيد", "row_pending_bg"),
            ("نص بانتظار الترصيد", "row_pending_text"),
            ("خلفية تم الترصيد", "row_reconciled_bg"),
            ("نص تم الترصيد", "row_reconciled_text"),
            ("خلفية صندوق الرصيد", "balance_box_bg"),
            ("نص صندوق الرصيد", "balance_box_text")
        ]

        self.color_vars = {}
        self.color_buttons = {}

        def choose_color(key, var):
            color = colorchooser.askcolor(title=f"اختر اللون لـ {key}", initialcolor=var.get())[1]
            if color:
                var.set(color)
                self.color_buttons[key].config(bg=color)

        for i, (label, key) in enumerate(color_settings):
            tk.Label(colors_grid, text=label, font=("Arial", 11)).grid(row=i, column=0, sticky="e", pady=5, padx=10)
            var = tk.StringVar(value=self.settings["colors"].get(key, "#000000"))
            self.color_vars[key] = var
            btn = tk.Button(colors_grid, text="اختر لون", command=lambda k=key, v=var: choose_color(k, v),
                          width=15, bg=var.get())
            btn.grid(row=i, column=1, pady=5, padx=10)
            self.color_buttons[key] = btn

        tk.Label(tables_frame, text="إعدادات الجداول", font=("Arial", 14, "bold")).pack(pady=10)

        tables_grid = tk.Frame(tables_frame)
        tables_grid.pack(pady=10)

        tk.Label(tables_grid, text="ارتفاع الصف:", font=("Arial", 11)).grid(row=0, column=0, sticky="e", pady=5, padx=10)
        self.row_height_var = tk.IntVar(value=self.settings["table"].get("row_height", 25))
        tk.Spinbox(tables_grid, from_=15, to=50, textvariable=self.row_height_var, width=10, font=("Arial", 11)).grid(row=0, column=1, pady=5, padx=10)

        tk.Label(tables_grid, text="حاشية الخلية:", font=("Arial", 11)).grid(row=1, column=0, sticky="e", pady=5, padx=10)
        self.cell_padding_var = tk.IntVar(value=self.settings["table"].get("cell_padding", 5))
        tk.Spinbox(tables_grid, from_=0, to=20, textvariable=self.cell_padding_var, width=10, font=("Arial", 11)).grid(row=1, column=1, pady=5, padx=10)

        tk.Label(tables_grid, text="سمك الحدود:", font=("Arial", 11)).grid(row=2, column=0, sticky="e", pady=5, padx=10)
        self.border_width_var = tk.IntVar(value=self.settings["table"].get("border_width", 1))
        tk.Spinbox(tables_grid, from_=0, to=5, textvariable=self.border_width_var, width=10, font=("Arial", 11)).grid(row=2, column=1, pady=5, padx=10)

        tk.Label(tables_grid, text="تباعد الأسطر:", font=("Arial", 11)).grid(row=3, column=0, sticky="e", pady=5, padx=10)
        self.line_spacing_var = tk.DoubleVar(value=self.settings["table"].get("line_spacing", 1.2))
        tk.Spinbox(tables_grid, from_=1.0, to=2.0, increment=0.1, textvariable=self.line_spacing_var, width=10, font=("Arial", 11)).grid(row=3, column=1, pady=5, padx=10)

        tk.Label(tables_grid, text="الحشو العمودي:", font=("Arial", 11)).grid(row=4, column=0, sticky="e", pady=5, padx=10)
        self.vertical_padding_var = tk.IntVar(value=self.settings["table"].get("vertical_padding", 3))
        tk.Spinbox(tables_grid, from_=0, to=10, textvariable=self.vertical_padding_var, width=10, font=("Arial", 11)).grid(row=4, column=1, pady=5, padx=10)

        # إعدادات محاذاة النص للتقارير
        tk.Label(tables_frame, text="محاذاة نص التقرير اليومي:", font=("Arial", 11)).pack(pady=(20, 5))
        self.daily_align_var = tk.StringVar(value=self.settings["daily_report"].get("text_align", "center"))
        align_frame_daily = tk.Frame(tables_frame)
        align_frame_daily.pack(pady=5)
        tk.Radiobutton(align_frame_daily, text="توسيط", variable=self.daily_align_var, value="center").pack(side=tk.RIGHT, padx=10)
        tk.Radiobutton(align_frame_daily, text="يمين", variable=self.daily_align_var, value="right").pack(side=tk.RIGHT, padx=10)
        tk.Radiobutton(align_frame_daily, text="يسار", variable=self.daily_align_var, value="left").pack(side=tk.RIGHT, padx=10)

        tk.Label(tables_frame, text="محاذاة رأس جدول التقرير اليومي:", font=("Arial", 11)).pack(pady=(10, 5))
        self.daily_header_align_var = tk.StringVar(value=self.settings["daily_report"].get("header_align", "center"))
        header_align_frame_daily = tk.Frame(tables_frame)
        header_align_frame_daily.pack(pady=5)
        tk.Radiobutton(header_align_frame_daily, text="توسيط", variable=self.daily_header_align_var, value="center").pack(side=tk.RIGHT, padx=10)
        tk.Radiobutton(header_align_frame_daily, text="يمين", variable=self.daily_header_align_var, value="right").pack(side=tk.RIGHT, padx=10)
        tk.Radiobutton(header_align_frame_daily, text="يسار", variable=self.daily_header_align_var, value="left").pack(side=tk.RIGHT, padx=10)

        tk.Label(tables_frame, text="محاذاة نص تقرير الاستعلام:", font=("Arial", 11)).pack(pady=(20, 5))
        self.query_align_var = tk.StringVar(value=self.settings["query_report"].get("text_align", "center"))
        align_frame_query = tk.Frame(tables_frame)
        align_frame_query.pack(pady=5)
        tk.Radiobutton(align_frame_query, text="توسيط", variable=self.query_align_var, value="center").pack(side=tk.RIGHT, padx=10)
        tk.Radiobutton(align_frame_query, text="يمين", variable=self.query_align_var, value="right").pack(side=tk.RIGHT, padx=10)
        tk.Radiobutton(align_frame_query, text="يسار", variable=self.query_align_var, value="left").pack(side=tk.RIGHT, padx=10)

        tk.Label(tables_frame, text="محاذاة رأس جدول تقرير الاستعلام:", font=("Arial", 11)).pack(pady=(10, 5))
        self.query_header_align_var = tk.StringVar(value=self.settings["query_report"].get("header_align", "center"))
        header_align_frame_query = tk.Frame(tables_frame)
        header_align_frame_query.pack(pady=5)
        tk.Radiobutton(header_align_frame_query, text="توسيط", variable=self.query_header_align_var, value="center").pack(side=tk.RIGHT, padx=10)
        tk.Radiobutton(header_align_frame_query, text="يمين", variable=self.query_header_align_var, value="right").pack(side=tk.RIGHT, padx=10)
        tk.Radiobutton(header_align_frame_query, text="يسار", variable=self.query_header_align_var, value="left").pack(side=tk.RIGHT, padx=10)

        tk.Label(tables_frame, text="عرض أعمدة التقرير اليومي (مفصولة بفاصلة):", font=("Arial", 11)).pack(pady=(20, 5))
        self.daily_cols_var = tk.StringVar(value=",".join(map(str, self.settings["daily_report"]["col_widths"])))
        tk.Entry(tables_frame, textvariable=self.daily_cols_var, width=40, font=("Arial", 11)).pack(pady=5)

        tk.Label(tables_frame, text="عرض أعمدة تقرير الاستعلام (مفصولة بفاصلة):", font=("Arial", 11)).pack(pady=(20, 5))
        self.query_cols_var = tk.StringVar(value=",".join(map(str, self.settings["query_report"]["col_widths"])))
        tk.Entry(tables_frame, textvariable=self.query_cols_var, width=40, font=("Arial", 11)).pack(pady=5)

        tk.Label(margins_frame, text="هوامش الصفحة (بالنقاط)", font=("Arial", 14, "bold")).pack(pady=10)

        margins_grid = tk.Frame(margins_frame)
        margins_grid.pack(pady=10)

        margin_settings = [
            ("الهامش العلوي", "top", 40),
            ("الهامش السفلي", "bottom", 40),
            ("الهامش الأيمن", "right", 50),
            ("الهامش الأيسر", "left", 50)
        ]

        self.margin_vars = {}
        for i, (label, key, default) in enumerate(margin_settings):
            tk.Label(margins_grid, text=label, font=("Arial", 11)).grid(row=i, column=0, sticky="e", pady=5, padx=10)
            var = tk.IntVar(value=self.settings["margins"].get(key, default))
            self.margin_vars[key] = var
            tk.Spinbox(margins_grid, from_=20, to=100, textvariable=var, width=10, font=("Arial", 11)).grid(row=i, column=1, pady=5, padx=10)

        btn_frame = tk.Frame(settings_win)
        btn_frame.pack(pady=20)

        def save_all_settings():
            for key, var in self.font_vars.items():
                self.settings["fonts"][key] = var.get()

            for key, var in self.color_vars.items():
                self.settings["colors"][key] = var.get()

            self.settings["table"]["row_height"] = self.row_height_var.get()
            self.settings["table"]["cell_padding"] = self.cell_padding_var.get()
            self.settings["table"]["border_width"] = self.border_width_var.get()
            self.settings["table"]["line_spacing"] = self.line_spacing_var.get()
            self.settings["table"]["vertical_padding"] = self.vertical_padding_var.get()

            # حفظ إعدادات المحاذاة للتقارير
            self.settings["daily_report"]["text_align"] = self.daily_align_var.get()
            self.settings["daily_report"]["header_align"] = self.daily_header_align_var.get()
            self.settings["query_report"]["text_align"] = self.query_align_var.get()
            self.settings["query_report"]["header_align"] = self.query_header_align_var.get()

            try:
                self.settings["daily_report"]["col_widths"] = [int(x.strip()) for x in self.daily_cols_var.get().split(",")]
                self.settings["query_report"]["col_widths"] = [int(x.strip()) for x in self.query_cols_var.get().split(",")]
            except:
                messagebox.showerror("خطأ", "يرجى إدخال أرقام صحيحة لعرض الأعمدة")
                return

            for key, var in self.margin_vars.items():
                self.settings["margins"][key] = var.get()

            if self.save_settings():
                messagebox.showinfo("نجاح", "تم حفظ الإعدادات بنجاح!\nسيتم تطبيقها على التقارير الجديدة.")
                settings_win.destroy()

        tk.Button(btn_frame, text="حفظ الإعدادات", command=save_all_settings,
                 bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), width=15).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="إلغاء", command=settings_win.destroy,
                 bg="#757575", fg="white", font=("Arial", 11), width=10).pack(side=tk.LEFT, padx=10)

        def reset_to_defaults():
            if messagebox.askyesno("تأكيد", "هل تريد استعادة الإعدادات الافتراضية؟"):
                self.settings = self.default_settings.copy()
                settings_win.destroy()
                self.open_settings_window()

        tk.Button(settings_win, text="استعادة الافتراضي", command=reset_to_defaults,
                 bg="#FF9800", fg="white", font=("Arial", 10)).pack(pady=10)

    def open_monthly_balance(self):
        balance_window = tk.Toplevel(self.root)
        balance_window.title("الموازنة بنطاق تاريخي")
        balance_window.geometry("700x600")
        balance_window.resizable(True, True)

        tk.Label(balance_window, text=" الموازنة بنطاق تاريخي", font=("Arial", 16, "bold")).pack(pady=10)

        date_frame = tk.Frame(balance_window, padx=20, pady=10)
        date_frame.pack(fill=tk.X)

        tk.Label(date_frame, text="من تاريخ:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="e", pady=5, padx=5)
        date_from_entry = tk.Entry(date_frame, font=("Arial", 12), width=15)
        date_from_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_from_entry.grid(row=0, column=1, pady=5, padx=5)

        tk.Label(date_frame, text="إلى تاريخ:", font=("Arial", 12, "bold")).grid(row=0, column=2, sticky="e", pady=5, padx=5)
        date_to_entry = tk.Entry(date_frame, font=("Arial", 12), width=15)
        date_to_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_to_entry.grid(row=0, column=3, pady=5, padx=5)

        quick_frame = tk.Frame(balance_window, padx=20, pady=5)
        quick_frame.pack(fill=tk.X)

        tk.Label(quick_frame, text="نطاقات سريعة:", font=("Arial", 11, "bold")).pack(side=tk.RIGHT, padx=5)

        def set_last_7_days():
            today = datetime.now()
            last_week = today - timedelta(days=6)
            date_from_entry.delete(0, tk.END)
            date_from_entry.insert(0, last_week.strftime("%Y-%m-%d"))
            date_to_entry.delete(0, tk.END)
            date_to_entry.insert(0, today.strftime("%Y-%m-%d"))

        def set_last_30_days():
            today = datetime.now()
            last_month = today - timedelta(days=29)
            date_from_entry.delete(0, tk.END)
            date_from_entry.insert(0, last_month.strftime("%Y-%m-%d"))
            date_to_entry.delete(0, tk.END)
            date_to_entry.insert(0, today.strftime("%Y-%m-%d"))

        def set_current_month():
            today = datetime.now()
            first_day = today.replace(day=1)
            date_from_entry.delete(0, tk.END)
            date_from_entry.insert(0, first_day.strftime("%Y-%m-%d"))
            date_to_entry.delete(0, tk.END)
            date_to_entry.insert(0, today.strftime("%Y-%m-%d"))

        def set_last_month():
            today = datetime.now()
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            first_day_last_month = last_day_last_month.replace(day=1)
            date_from_entry.delete(0, tk.END)
            date_from_entry.insert(0, first_day_last_month.strftime("%Y-%m-%d"))
            date_to_entry.delete(0, tk.END)
            date_to_entry.insert(0, last_day_last_month.strftime("%Y-%m-%d"))

        def set_custom_year():
            year = datetime.now().year
            date_from_entry.delete(0, tk.END)
            date_from_entry.insert(0, f"{year}-01-01")
            date_to_entry.delete(0, tk.END)
            date_to_entry.insert(0, f"{year}-12-31")

        tk.Button(quick_frame, text="آخر 7 أيام", command=set_last_7_days, font=("Arial", 10), width=12).pack(side=tk.RIGHT, padx=3)
        tk.Button(quick_frame, text="آخر 30 يوم", command=set_last_30_days, font=("Arial", 10), width=12).pack(side=tk.RIGHT, padx=3)
        tk.Button(quick_frame, text="الشهر الحالي", command=set_current_month, font=("Arial", 10), width=12).pack(side=tk.RIGHT, padx=3)
        tk.Button(quick_frame, text="الشهر الماضي", command=set_last_month, font=("Arial", 10), width=12).pack(side=tk.RIGHT, padx=3)
        tk.Button(quick_frame, text="السنة الحالية", command=set_custom_year, font=("Arial", 10), width=12).pack(side=tk.RIGHT, padx=3)

        def calculate_balance():
            date_from = date_from_entry.get().strip()
            date_to = date_to_entry.get().strip()

            if not date_from or not date_to:
                messagebox.showerror("خطأ", "يرجى إدخال تاريخ البداية والنهاية.")
                return

            try:
                datetime.strptime(date_from, "%Y-%m-%d")
                datetime.strptime(date_to, "%Y-%m-%d")
            except:
                messagebox.showerror("خطأ", "صيغة التاريخ يجب أن تكون YYYY-MM-DD")
                return

            if date_from > date_to:
                messagebox.showerror("خطأ", "تاريخ البداية يجب أن يكون قبل تاريخ النهاية.")
                return

            range_records = []
            for rec in self.records:
                rec_date = rec.get("date", "")
                if date_from <= rec_date <= date_to:
                    if not rec.get("deleted"):
                        range_records.append(rec)

            if not range_records:
                messagebox.showinfo("معلومات", f"لا توجد سندات في النطاق من {date_from} إلى {date_to}")
                return

            total_qabd = {"ل.س": 0, "$": 0, "€": 0}
            total_sarf = {"ل.س": 0, "$": 0, "€": 0}
            total_tasreef_impact = {"ل.س": 0, "$": 0, "€": 0}

            for rec in range_records:
                order_type = rec.get("type")
                currency = rec.get("currency", "ل.س")
                try:
                    amount = float(rec.get("amount", 0))
                except:
                    amount = 0

                if order_type == "قبض":
                    total_qabd[currency] += amount
                elif order_type == "صرف":
                    total_sarf[currency] += amount
                elif order_type == "تصريف":
                    impact_syp = rec.get("impact_SYP", 0)
                    impact_usd = rec.get("impact_USD", 0)
                    impact_eur = rec.get("impact_EUR", 0)
                    total_tasreef_impact["ل.س"] += impact_syp
                    total_tasreef_impact["$"] += impact_usd
                    total_tasreef_impact["€"] += impact_eur

            result_window = tk.Toplevel(balance_window)
            result_window.title(f"نتائج الموازنة: {date_from} إلى {date_to}")
            result_window.geometry("600x500")

            tk.Label(result_window, text=f"📊 الموازنة: من {date_from} إلى {date_to}",
                    font=("Arial", 14, "bold")).pack(pady=10)

            result_frame = tk.Frame(result_window, padx=20, pady=10)
            result_frame.pack(fill=tk.BOTH, expand=True)

            tk.Label(result_frame, text="إجمالي القبضات:", font=("Arial", 12, "bold"), fg="#2e7d32").grid(row=0, column=0, sticky="e", pady=5)
            tk.Label(result_frame, text=f"ل.س: {format_number(total_qabd['ل.س'])}", font=("Arial", 11)).grid(row=0, column=1, padx=10)
            tk.Label(result_frame, text=f"$: {format_number(total_qabd['$'])}", font=("Arial", 11)).grid(row=0, column=2, padx=10)
            tk.Label(result_frame, text=f"€: {format_number(total_qabd['€'])}", font=("Arial", 11)).grid(row=0, column=3, padx=10)

            tk.Label(result_frame, text="إجمالي المصروفات:", font=("Arial", 12, "bold"), fg="#c62828").grid(row=1, column=0, sticky="e", pady=5)
            tk.Label(result_frame, text=f"ل.س: {format_number(total_sarf['ل.س'])}", font=("Arial", 11)).grid(row=1, column=1, padx=10)
            tk.Label(result_frame, text=f"$: {format_number(total_sarf['$'])}", font=("Arial", 11)).grid(row=1, column=2, padx=10)
            tk.Label(result_frame, text=f"€: {format_number(total_sarf['€'])}", font=("Arial", 11)).grid(row=1, column=3, padx=10)

            tk.Label(result_frame, text="تأثير التصريف:", font=("Arial", 12, "bold"), fg="#1565c0").grid(row=2, column=0, sticky="e", pady=5)
            tk.Label(result_frame, text=f"ل.س: {format_number(total_tasreef_impact['ل.س'])}", font=("Arial", 11)).grid(row=2, column=1, padx=10)
            tk.Label(result_frame, text=f"$: {format_number(total_tasreef_impact['$'])}", font=("Arial", 11)).grid(row=2, column=2, padx=10)
            tk.Label(result_frame, text=f"€: {format_number(total_tasreef_impact['€'])}", font=("Arial", 11)).grid(row=2, column=3, padx=10)

            tk.Label(result_frame, text="صافي الحركة:", font=("Arial", 12, "bold"), fg="#6a1b9a").grid(row=3, column=0, sticky="e", pady=10)
            net_syp = total_qabd['ل.س'] - total_sarf['ل.س'] + total_tasreef_impact['ل.س']
            net_usd = total_qabd['$'] - total_sarf['$'] + total_tasreef_impact['$']
            net_eur = total_qabd['€'] - total_sarf['€'] + total_tasreef_impact['€']
            tk.Label(result_frame, text=f"ل.س: {format_number(net_syp)}", font=("Arial", 11, "bold")).grid(row=3, column=1, padx=10)
            tk.Label(result_frame, text=f"$: {format_number(net_usd)}", font=("Arial", 11, "bold")).grid(row=3, column=2, padx=10)
            tk.Label(result_frame, text=f"€: {format_number(net_eur)}", font=("Arial", 11, "bold")).grid(row=3, column=3, padx=10)

            tk.Label(result_frame, text="عدد السندات:", font=("Arial", 12, "bold")).grid(row=4, column=0, sticky="e", pady=5)
            tk.Label(result_frame, text=f"{len(range_records)} سند", font=("Arial", 11)).grid(row=4, column=1, columnspan=3, padx=10)

            def export_balance_report():
                today_folder = self.get_today_folder()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_path = os.path.join(today_folder, f"Balance_Report_{date_from}_to_{date_to}_{timestamp}.pdf")

                try:
                    font_name = 'Helvetica'
                    if FONT_PATH and os.path.exists(FONT_PATH):
                        pdfmetrics.registerFont(TTFont('WinFont', FONT_PATH))
                        font_name = 'WinFont'

                    c = canvas.Canvas(report_path, pagesize=A4)
                    width, height = A4

                    c.setFont(font_name, 16)
                    c.drawCentredString(width/2, height - 40, reshape_text(f"تقرير الموازنة: من {date_from} إلى {date_to}"))

                    y = height - 80

                    col_widths = [150, 100, 100, 100]
                    headers = ["البند", "ليرة سورية", "دولار", "يورو"]

                    def draw_header(yy):
                        c.setFillColor(colors.Color(0.85, 0.9, 0.95))
                        x = width - 50
                        for header, w in zip(headers, col_widths):
                            c.rect(x - w, yy - 5, w, 20, fill=1, stroke=1)
                            c.setFillColor(colors.black)
                            c.drawCentredString(x - w/2, yy, reshape_text(header))
                            x -= w
                            c.setFillColor(colors.Color(0.85, 0.9, 0.95))
                        c.setFillColor(colors.black)

                    draw_header(y)
                    y -= 30

                    c.setFont(font_name, 10)
                    rows = [
                        ("إجمالي القبضات", total_qabd['ل.س'], total_qabd['$'], total_qabd['€']),
                        ("إجمالي المصروفات", total_sarf['ل.س'], total_sarf['$'], total_sarf['€']),
                        ("تأثير التصريف", total_tasreef_impact['ل.س'], total_tasreef_impact['$'], total_tasreef_impact['€']),
                        ("صافي الحركة", net_syp, net_usd, net_eur)
                    ]

                    for row in rows:
                        x = width - 50
                        for val, w in zip(row, col_widths):
                            c.setFillColor(colors.white)
                            c.rect(x - w, y - 5, w, 18, fill=1, stroke=1)
                            c.setFillColor(colors.black)
                            if isinstance(val, str):
                                c.drawCentredString(x - w/2, y - 2, reshape_text(val))
                            else:
                                c.drawCentredString(x - w/2, y - 2, format_number(val))
                            x -= w
                        y -= 22

                    c.save()

                    if sys.platform == "win32":
                        os.startfile(report_path)
                    elif sys.platform == "darwin":
                        subprocess.call(["open", report_path])
                    else:
                        subprocess.call(["xdg-open", report_path])

                    messagebox.showinfo("نجاح", f"تم تصدير تقرير الموازنة\nالمسار: {report_path}")

                except Exception as e:
                    messagebox.showerror("خطأ", f"حدث خطأ أثناء التصدير: {str(e)}")

            tk.Button(result_window, text="تصدير التقرير PDF", command=export_balance_report,
                     bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), width=15).pack(pady=10)

        tk.Button(date_frame, text="احسب الموازنة", command=calculate_balance,
                 bg="#607D8B", fg="white", font=("Arial", 12, "bold"), width=15).grid(row=0, column=4, padx=10)

    def check_sufficient_balance(self, order_type, amount, currency, exchange_info=None):
        try:
            amount = float(amount)
        except:
            return True, ""

        if order_type == "صرف":
            if self.balance.get(currency, 0) < amount:
                return False, f"الرصيد غير كافٍ!\nالرصيد الحالي: {format_number(self.balance.get(currency, 0))} {currency}\nالمبلغ المطلوب: {format_number(amount)} {currency}"

        elif order_type == "تصريف" and exchange_info:
            ex_type = exchange_info.get("type")
            ex_amount = float(exchange_info.get("amount", 0))
            ex_result = extract_number_from_text(exchange_info.get("result", "0"))

            impact = self.calculate_exchange_impact(ex_type, ex_amount, ex_result, currency)

            if impact["ل.س"] < 0 and self.balance.get("ل.س", 0) < abs(impact["ل.س"]):
                return False, f"الرصيد غير كافٍ بالليرة السورية!\nالرصيد الحالي: {format_number(self.balance.get('ل.س', 0))} ل.س\nالمطلوب: {format_number(abs(impact['ل.س']))} ل.س"

            if impact["$"] < 0 and self.balance.get("$", 0) < abs(impact["$"]):
                return False, f"الرصيد غير كافٍ بالدولار!\nالرصيد الحالي: {format_number(self.balance.get('$', 0))} $\nالمطلوب: {format_number(abs(impact['$']))} $"

            if impact["€"] < 0 and self.balance.get("€", 0) < abs(impact["€"]):
                return False, f"الرصيد غير كافٍ باليورو!\nالرصيد الحالي: {format_number(self.balance.get('€', 0))} €\nالمطلوب: {format_number(abs(impact['€']))} €"

        return True, ""

    def check_pending_reconciliation(self):
        pending = [r for r in self.records if r.get("needs_reconciliation") and not r.get("reconciled")]
        if pending:
            if messagebox.askyesno("📋 تنبيه الترصيد",
                f"يوجد {len(pending)} سند في قائمة الترصيد.\n\nهل تريد فتح قائمة الترصيد الآن؟"):
                self.open_reconciliation_window()

    def open_reconciliation_window(self):
        recon_window = tk.Toplevel(self.root)
        recon_window.title("قائمة الترصيد - السندات المعلقة")
        recon_window.geometry("800x600")
        recon_window.resizable(True, True)

        tk.Label(recon_window, text="📋 قائمة السندات التي تحتاج ترصيد", font=("Arial", 16, "bold")).pack(pady=10)

        pending_records = [r for r in self.records if r.get("needs_reconciliation") and not r.get("reconciled")]
        reconciled_records = [r for r in self.records if r.get("needs_reconciliation") and r.get("reconciled")]

        stats_frame = tk.Frame(recon_window, bg="#e3f2fd", padx=15, pady=10)
        stats_frame.pack(fill=tk.X, padx=20, pady=5)

        tk.Label(stats_frame, text=f" معلقة: {len(pending_records)}",
                font=("Arial", 12, "bold"), bg="#e3f2fd", fg="#f57f17").pack(side=tk.RIGHT, padx=20)
        tk.Label(stats_frame, text=f"✅ تم الترصيد: {len(reconciled_records)}",
                font=("Arial", 12, "bold"), bg="#e3f2fd", fg="#2e7d32").pack(side=tk.RIGHT, padx=20)

        list_frame = tk.Frame(recon_window, padx=20, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(list_frame, text="السندات المعلقة:", font=("Arial", 11, "bold")).pack(anchor="w")

        canvas_frame = tk.Frame(list_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        tk_canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=tk_canvas.yview)
        scrollable_frame = tk.Frame(tk_canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: tk_canvas.configure(scrollregion=tk_canvas.bbox("all"))
        )

        tk_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        tk_canvas.configure(yscrollcommand=scrollbar.set)

        tk_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        checkboxes = {}

        def load_pending_records():
            for widget in scrollable_frame.winfo_children():
                widget.destroy()
            checkboxes.clear()

            pending = [r for r in self.records if r.get("needs_reconciliation") and not r.get("reconciled")]

            if not pending:
                tk.Label(scrollable_frame, text="لا توجد سندات معلقة للترصيد.",
                        font=("Arial", 12), fg="green").pack(pady=20)
                return

            header_frame = tk.Frame(scrollable_frame, bg="#fff9c4")
            header_frame.pack(fill=tk.X, pady=2)

            tk.Label(header_frame, text="✓", font=("Arial", 10, "bold"), bg="#fff9c4", width=3).pack(side=tk.RIGHT, padx=2)
            tk.Label(header_frame, text="النوع", font=("Arial", 10, "bold"), bg="#fff9c4", width=8).pack(side=tk.RIGHT, padx=2)
            tk.Label(header_frame, text="الرقم", font=("Arial", 10, "bold"), bg="#fff9c4", width=8).pack(side=tk.RIGHT, padx=2)
            tk.Label(header_frame, text="المبلغ", font=("Arial", 10, "bold"), bg="#fff9c4", width=15).pack(side=tk.RIGHT, padx=2)
            tk.Label(header_frame, text="حامل السند", font=("Arial", 10, "bold"), bg="#fff9c4", width=20).pack(side=tk.RIGHT, padx=2)
            tk.Label(header_frame, text="البيان", font=("Arial", 10, "bold"), bg="#fff9c4", width=25).pack(side=tk.RIGHT, padx=2)
            tk.Label(header_frame, text="التاريخ والوقت", font=("Arial", 10, "bold"), bg="#fff9c4", width=15).pack(side=tk.RIGHT, padx=2)

            for idx, rec in enumerate(pending):
                row_frame = tk.Frame(scrollable_frame)
                row_frame.pack(fill=tk.X, pady=1)

                var = tk.BooleanVar(value=False)
                cb = tk.Checkbutton(row_frame, variable=var, width=3)
                cb.pack(side=tk.RIGHT, padx=2)

                tk.Label(row_frame, text=rec.get("type", ""), width=8).pack(side=tk.RIGHT, padx=2)
                tk.Label(row_frame, text=rec.get("id", ""), width=8).pack(side=tk.RIGHT, padx=2)
                tk.Label(row_frame, text=f"{rec.get('amount', '')} {rec.get('currency', '')}", width=15).pack(side=tk.RIGHT, padx=2)
                tk.Label(row_frame, text=rec.get("payee", ""), width=20).pack(side=tk.RIGHT, padx=2)
                tk.Label(row_frame, text=rec.get("reason", ""), width=25).pack(side=tk.RIGHT, padx=2)
                tk.Label(row_frame, text=rec.get("datetime", rec.get("date", "")), width=15).pack(side=tk.RIGHT, padx=2)

                checkboxes[idx] = (rec, var)

        def select_all():
            for rec, var in checkboxes.values():
                var.set(True)

        def deselect_all():
            for rec, var in checkboxes.values():
                var.set(False)

        def mark_reconciled():
            selected = [(rec, var) for rec, var in checkboxes.values() if var.get()]
            if not selected:
                messagebox.showwarning("تحذير", "لم يتم تحديد أي سند.")
                return

            if not messagebox.askyesno("تأكيد", f"هل تريد تأكيد ترصيد {len(selected)} سند؟"):
                return

            self.create_backup(f"ترصيد {len(selected)} سند")

            reconciled_count = 0
            for rec, var in selected:
                rec["reconciled"] = True
                rec["reconciled_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                reconciled_count += 1

            self.save_records()
            messagebox.showinfo("نجاح", f"تم ترصيد {reconciled_count} سند بنجاح")
            recon_window.destroy()

        def generate_recon_report():
            pending = [r for r in self.records if r.get("needs_reconciliation") and not r.get("reconciled")]
            reconciled = [r for r in self.records if r.get("needs_reconciliation") and r.get("reconciled")]

            if not pending and not reconciled:
                messagebox.showinfo("معلومات", "لا توجد سندات للترصيد.")
                return

            today_folder = self.get_today_folder()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(today_folder, f"Reconciliation_Report_{timestamp}.pdf")

            try:
                from reportlab.pdfgen import canvas as pdf_canvas
                font_name = 'Helvetica'
                if FONT_PATH and os.path.exists(FONT_PATH):
                    pdfmetrics.registerFont(TTFont('WinFont', FONT_PATH))
                    font_name = 'WinFont'

                c = pdf_canvas.Canvas(report_path, pagesize=A4)
                width, height = A4

                c.setFont(font_name, 16)
                c.drawCentredString(width/2, height - 40, reshape_text("تقرير الترصيد"))

                c.setFont(font_name, 11)
                c.drawString(50, height - 70, f"السندات المعلقة: {len(pending)}")
                c.drawString(50, height - 85, f"السندات التي تم الترصيد: {len(reconciled)}")

                y = height - 120

                if pending:
                    c.setFont(font_name, 14)
                    c.setFillColor(colors.Color(0.95, 0.85, 0.5))
                    c.drawCentredString(width/2, y, reshape_text("⏳ السندات المعلقة"))
                    c.setFillColor(colors.black)
                    y -= 30

                    col_widths = [50, 60, 80, 100, 120, 100, 90]
                    headers = ["النوع", "الرقم", "التاريخ", "المبلغ", "حامل السند", "البيان", "الوقت"]

                    c.setFillColor(colors.Color(0.85, 0.9, 0.95))
                    x = width - 50
                    for header, w in zip(headers, col_widths):
                        c.rect(x - w, y - 5, w, 20, fill=1, stroke=1)
                        c.setFillColor(colors.black)
                        c.drawCentredString(x - w/2, y, reshape_text(header))
                        x -= w
                        c.setFillColor(colors.Color(0.85, 0.9, 0.95))
                    c.setFillColor(colors.black)
                    y -= 30

                    c.setFont(font_name, 8)
                    for rec in pending:
                        if y < 50:
                            c.showPage()
                            y = height - 50
                            c.setFillColor(colors.black)
                            c.setFont(font_name, 8)
                        row_data = [
                            rec.get("type", ""),
                            rec.get("id", ""),
                            rec.get("date", ""),
                            rec.get("amount", "") + " " + rec.get("currency", ""),
                            rec.get("payee", ""),
                            rec.get("reason", ""),
                            rec.get("datetime", rec.get("date", ""))
                        ]
                        x = width - 50
                        for val, w in zip(row_data, col_widths):
                            c.setFillColor(colors.Color(1, 0.95, 0.8))
                            c.rect(x - w, y - 5, w, 16, fill=1, stroke=1)
                            c.setFillColor(colors.black)
                            text_val = str(val)[:15] if len(str(val)) > 15 else str(val)
                            c.drawCentredString(x - w/2, y - 2, reshape_text(text_val))
                            x -= w
                        y -= 22

                c.save()

                if sys.platform == "win32":
                    os.startfile(report_path)
                elif sys.platform == "darwin":
                    subprocess.call(["open", report_path])
                else:
                    subprocess.call(["xdg-open", report_path])

                messagebox.showinfo("نجاح", f"تم إنشاء تقرير الترصيد\nالمسار: {report_path}")

            except Exception as e:
                messagebox.showerror("خطأ", f"حدث خطأ: {str(e)}")

        load_pending_records()

        ctrl_frame = tk.Frame(recon_window)
        ctrl_frame.pack(pady=10)

        tk.Button(ctrl_frame, text="تحديد الكل", command=select_all, bg="#4CAF50", fg="white", font=("Arial", 11), width=12).pack(side=tk.RIGHT, padx=5)
        tk.Button(ctrl_frame, text="إلغاء الكل", command=deselect_all, bg="#FF9800", fg="white", font=("Arial", 11), width=12).pack(side=tk.RIGHT, padx=5)
        tk.Button(ctrl_frame, text="تم الترصيد ✓", command=mark_reconciled, bg="#9C27B0", fg="white", font=("Arial", 11, "bold"), width=15).pack(side=tk.RIGHT, padx=5)
        tk.Button(ctrl_frame, text="تقرير الترصيد", command=generate_recon_report, bg="#2196F3", fg="white", font=("Arial", 11), width=12).pack(side=tk.RIGHT, padx=5)
        tk.Button(ctrl_frame, text="إغلاق", command=recon_window.destroy, bg="#757575", fg="white", font=("Arial", 11), width=10).pack(side=tk.RIGHT, padx=5)

    def open_delete_window(self):
        delete_window = tk.Toplevel(self.root)
        delete_window.title("حذف مجموعة سندات")
        delete_window.geometry("750x600")
        delete_window.resizable(True, True)

        tk.Label(delete_window, text="حذف مجموعة سندات حسب النطاق", font=("Arial", 16, "bold")).pack(pady=10)

        range_frame = tk.Frame(delete_window, padx=20, pady=10)
        range_frame.pack(fill=tk.X)

        tk.Label(range_frame, text="من رقم:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="e", padx=5, pady=5)
        id_from_entry = tk.Entry(range_frame, font=("Arial", 12), width=10, justify="center")
        id_from_entry.grid(row=0, column=1, padx=5, pady=5)
        id_from_entry.focus()

        tk.Label(range_frame, text="إلى رقم:", font=("Arial", 12, "bold")).grid(row=0, column=2, sticky="e", padx=5, pady=5)
        id_to_entry = tk.Entry(range_frame, font=("Arial", 12), width=10, justify="center")
        id_to_entry.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(range_frame, text="نوع السند:", font=("Arial", 12, "bold")).grid(row=0, column=4, sticky="e", padx=5, pady=5)
        delete_type_var = tk.StringVar(value="الكل")
        type_combo = ttk.Combobox(range_frame, textvariable=delete_type_var, values=["الكل", "صرف", "قبض", "تصريف"], state="readonly", width=10)
        type_combo.grid(row=0, column=5, padx=5, pady=5)

        show_deleted_var = tk.BooleanVar(value=False)
        tk.Checkbutton(range_frame, text="عرض المحذوفة", variable=show_deleted_var, font=("Arial", 10)).grid(row=0, column=6, padx=5)

        list_frame = tk.Frame(delete_window, padx=20, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(list_frame, text="السندات الموجودة في النطاق:", font=("Arial", 11, "bold")).pack(anchor="w")

        canvas_frame = tk.Frame(list_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        tk_canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=tk_canvas.yview)
        scrollable_frame = tk.Frame(tk_canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: tk_canvas.configure(scrollregion=tk_canvas.bbox("all"))
        )

        tk_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        tk_canvas.configure(yscrollcommand=scrollbar.set)

        tk_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        checkboxes = {}

        def load_records_in_range():
            for widget in scrollable_frame.winfo_children():
                widget.destroy()
            checkboxes.clear()

            try:
                id_from = int(id_from_entry.get().strip())
                id_to = int(id_to_entry.get().strip())
            except:
                messagebox.showerror("خطأ", "يرجى إدخال أرقام صحيحة للنطاق.")
                return

            if id_from > id_to:
                messagebox.showerror("خطأ", "رقم البداية يجب أن يكون أصغر من رقم النهاية.")
                return

            found_records = []
            for i, rec in enumerate(self.records):
                try:
                    rec_id_num = int(rec.get("id", "0"))
                except:
                    continue

                if id_from <= rec_id_num <= id_to:
                    if delete_type_var.get() != "الكل" and rec.get("type") != delete_type_var.get():
                        continue

                    if show_deleted_var.get():
                        if rec.get("deleted"):
                            found_records.append((i, rec))
                    else:
                        if not rec.get("deleted"):
                            found_records.append((i, rec))

            if not found_records:
                tk.Label(scrollable_frame, text="لا توجد سندات في هذا النطاق.", font=("Arial", 11), fg="red").pack(pady=20)
                return

            header_frame = tk.Frame(scrollable_frame, bg="#e3f2fd")
            header_frame.pack(fill=tk.X, pady=2)

            tk.Label(header_frame, text="✓", font=("Arial", 10, "bold"), bg="#e3f2fd", width=3).pack(side=tk.RIGHT, padx=2)
            tk.Label(header_frame, text="الحالة", font=("Arial", 10, "bold"), bg="#e3f2fd", width=8).pack(side=tk.RIGHT, padx=2)
            tk.Label(header_frame, text="النوع", font=("Arial", 10, "bold"), bg="#e3f2fd", width=8).pack(side=tk.RIGHT, padx=2)
            tk.Label(header_frame, text="الرقم", font=("Arial", 10, "bold"), bg="#e3f2fd", width=8).pack(side=tk.RIGHT, padx=2)
            tk.Label(header_frame, text="المبلغ", font=("Arial", 10, "bold"), bg="#e3f2fd", width=15).pack(side=tk.RIGHT, padx=2)
            tk.Label(header_frame, text="حامل السند", font=("Arial", 10, "bold"), bg="#e3f2fd", width=20).pack(side=tk.RIGHT, padx=2)
            tk.Label(header_frame, text="التاريخ والوقت", font=("Arial", 10, "bold"), bg="#e3f2fd", width=15).pack(side=tk.RIGHT, padx=2)

            for idx, (record_index, rec) in enumerate(found_records):
                row_frame = tk.Frame(scrollable_frame)
                row_frame.pack(fill=tk.X, pady=1)

                var = tk.BooleanVar(value=False)
                cb = tk.Checkbutton(row_frame, variable=var, width=3)
                cb.pack(side=tk.RIGHT, padx=2)

                status = "محذوف" if rec.get("deleted") else ("معدل" if rec.get("edited") else "نشط")
                status_color = "red" if rec.get("deleted") else ("green" if rec.get("edited") else "black")

                tk.Label(row_frame, text=status, width=8, fg=status_color, font=("Arial", 9, "bold")).pack(side=tk.RIGHT, padx=2)
                tk.Label(row_frame, text=rec.get("type", ""), width=8).pack(side=tk.RIGHT, padx=2)
                tk.Label(row_frame, text=rec.get("id", ""), width=8).pack(side=tk.RIGHT, padx=2)
                tk.Label(row_frame, text=f"{rec.get('amount', '')} {rec.get('currency', '')}", width=15).pack(side=tk.RIGHT, padx=2)
                tk.Label(row_frame, text=rec.get("payee", ""), width=20).pack(side=tk.RIGHT, padx=2)
                tk.Label(row_frame, text=rec.get("datetime", rec.get("date", "")), width=15).pack(side=tk.RIGHT, padx=2)

                checkboxes[record_index] = var

        def select_all():
            for var in checkboxes.values():
                var.set(True)

        def deselect_all():
            for var in checkboxes.values():
                var.set(False)

        def delete_selected():
            selected_indices = [idx for idx, var in checkboxes.items() if var.get()]
            if not selected_indices:
                messagebox.showwarning("تحذير", "لم يتم تحديد أي سند للحذف.")
                return

            if not messagebox.askyesno("تأكيد", f"هل أنت متأكد من حذف {len(selected_indices)} سند؟\n\nسيتم عكس تأثيرها على الصندوق."):
                return

            self.create_backup(f"حذف {len(selected_indices)} سند")

            deleted_count = 0
            for idx in selected_indices:
                rec = self.records[idx]
                if not rec.get("deleted"):
                    self.reverse_record_impact(rec)
                    rec["deleted"] = True
                    rec["deleted_datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    deleted_count += 1

            self.save_records()
            self.update_balance_display()

            messagebox.showinfo("نجاح", f"تم حذف {deleted_count} سند (منطقياً)\nتم عكس تأثيرها على الصندوق\nالأرقام التسلسلية لم تتأثر.")
            delete_window.destroy()

        ctrl_frame = tk.Frame(delete_window)
        ctrl_frame.pack(pady=10)

        tk.Button(ctrl_frame, text="عرض السندات", command=load_records_in_range, bg="#2196F3", fg="white", font=("Arial", 11, "bold"), width=15).pack(side=tk.RIGHT, padx=5)
        tk.Button(ctrl_frame, text="تحديد الكل", command=select_all, bg="#4CAF50", fg="white", font=("Arial", 11), width=12).pack(side=tk.RIGHT, padx=5)
        tk.Button(ctrl_frame, text="إلغاء الكل", command=deselect_all, bg="#FF9800", fg="white", font=("Arial", 11), width=12).pack(side=tk.RIGHT, padx=5)
        tk.Button(ctrl_frame, text="حذف المحدد", command=delete_selected, bg="#E91E63", fg="white", font=("Arial", 11, "bold"), width=15).pack(side=tk.RIGHT, padx=5)
        tk.Button(ctrl_frame, text="إلغاء", command=delete_window.destroy, bg="#757575", fg="white", font=("Arial", 11), width=10).pack(side=tk.RIGHT, padx=5)

    def reverse_record_impact(self, record):
        order_type = record.get("type")
        currency = record.get("currency", "ل.س")
        try:
            amount = float(record.get("amount", 0))
        except:
            amount = 0

        if order_type == "قبض":
            self.balance[currency] = self.balance.get(currency, 0) - amount
        elif order_type == "صرف":
            self.balance[currency] = self.balance.get(currency, 0) + amount
        elif order_type == "تصريف":
            impact_syp = record.get("impact_SYP", 0)
            impact_usd = record.get("impact_USD", 0)
            impact_eur = record.get("impact_EUR", 0)
            self.balance["ل.س"] = self.balance.get("ل.س", 0) - impact_syp
            self.balance["$"] = self.balance.get("$", 0) - impact_usd
            self.balance["€"] = self.balance.get("€", 0) - impact_eur

        self.save_balance()

    def apply_record_impact(self, record):
        order_type = record.get("type")
        currency = record.get("currency", "ل.س")
        try:
            amount = float(record.get("amount", 0))
        except:
            amount = 0

        if order_type == "قبض":
            self.balance[currency] = self.balance.get(currency, 0) + amount
        elif order_type == "صرف":
            self.balance[currency] = self.balance.get(currency, 0) - amount
        elif order_type == "تصريف":
            impact_syp = record.get("impact_SYP", 0)
            impact_usd = record.get("impact_USD", 0)
            impact_eur = record.get("impact_EUR", 0)
            self.balance["ل.س"] = self.balance.get("ل.س", 0) + impact_syp
            self.balance["$"] = self.balance.get("$", 0) + impact_usd
            self.balance["€"] = self.balance.get("€", 0) + impact_eur

        self.save_balance()

    def open_edit_window(self):
        edit_window = tk.Toplevel(self.root)
        edit_window.title("تعديل سند")
        edit_window.geometry("400x200")
        edit_window.resizable(False, False)

        tk.Label(edit_window, text="إدخال رقم السند للتعديل", font=("Arial", 14, "bold")).pack(pady=15)

        frame = tk.Frame(edit_window, padx=20)
        frame.pack(fill=tk.X)

        tk.Label(frame, text="رقم السند:", font=("Arial", 12)).pack(side=tk.RIGHT, padx=5)
        record_id_entry = tk.Entry(frame, font=("Arial", 14), width=15, justify="center")
        record_id_entry.pack(side=tk.RIGHT, padx=5)
        record_id_entry.focus()

        def search_record():
            record_id = record_id_entry.get().strip()
            if not record_id:
                messagebox.showwarning("تحذير", "يرجى إدخال رقم السند.")
                return

            found_record = None
            record_index = None
            for i, rec in enumerate(self.records):
                if rec.get("id") == record_id or rec.get("id") == f"{int(record_id):04d}":
                    found_record = rec
                    record_index = i
                    break

            if not found_record:
                messagebox.showerror("خطأ", f"لم يتم العثور على سند برقم {record_id}")
                return

            edit_window.destroy()
            self.show_edit_form(found_record, record_index)

        tk.Button(edit_window, text="بحث", command=search_record, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), width=15).pack(pady=15)
        record_id_entry.bind('<Return>', lambda e: search_record())

    def show_edit_form(self, record, record_index):
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"تعديل سند رقم {record.get('id')}")
        edit_window.geometry("700x700")
        edit_window.resizable(True, True)

        original_record = record.copy()

        tk.Label(edit_window, text=f"تعديل سند رقم {record.get('id')}", font=("Arial", 16, "bold")).pack(pady=10)

        type_frame = tk.Frame(edit_window)
        type_frame.pack(pady=5)

        tk.Label(type_frame, text="نوع السند:", font=("Arial", 12, "bold")).pack(side=tk.RIGHT, padx=5)
        edit_type_var = tk.StringVar(value=record.get("type", "صرف"))

        tk.Radiobutton(type_frame, text="صرف", variable=edit_type_var, value="صرف", font=("Arial", 11)).pack(side=tk.RIGHT, padx=5)
        tk.Radiobutton(type_frame, text="قبض", variable=edit_type_var, value="قبض", font=("Arial", 11)).pack(side=tk.RIGHT, padx=5)
        tk.Radiobutton(type_frame, text="تصريف", variable=edit_type_var, value="تصريف", font=("Arial", 11)).pack(side=tk.RIGHT, padx=5)

        fields_frame = tk.Frame(edit_window, padx=20, pady=10)
        fields_frame.pack(fill=tk.X)

        tk.Label(fields_frame, text="المبلغ:", font=("Arial", 12)).grid(row=0, column=1, sticky="e", pady=5, padx=5)
        edit_amount_var = tk.StringVar(value=record.get("amount", ""))
        tk.Entry(fields_frame, font=("Arial", 12), width=20, textvariable=edit_amount_var, justify="right").grid(row=0, column=0, pady=5, padx=5, sticky="e")

        tk.Label(fields_frame, text="العملة:", font=("Arial", 12)).grid(row=1, column=1, sticky="e", pady=5, padx=5)
        edit_currency_var = tk.StringVar(value=record.get("currency", "ل.س"))
        ttk.Combobox(fields_frame, textvariable=edit_currency_var, values=["ل.س", "$", "€"], state="readonly", width=18).grid(row=1, column=0, pady=5, padx=5, sticky="e")

        tk.Label(fields_frame, text="المبلغ كتابة:", font=("Arial", 12)).grid(row=2, column=1, sticky="e", pady=5, padx=5)
        edit_amount_words_var = tk.StringVar(value=record.get("amount_words", ""))
        tk.Entry(fields_frame, font=("Arial", 12), width=30, textvariable=edit_amount_words_var, justify="right").grid(row=2, column=0, pady=5, padx=5, sticky="e")

        tk.Label(fields_frame, text="إلى أمين الصندوق:", font=("Arial", 12)).grid(row=3, column=1, sticky="e", pady=5, padx=5)
        edit_treasurer_var = tk.StringVar(value=record.get("treasurer", ""))
        tk.Entry(fields_frame, font=("Arial", 12), width=30, textvariable=edit_treasurer_var, justify="right").grid(row=3, column=0, pady=5, padx=5, sticky="e")

        tk.Label(fields_frame, text="إلى السيد / من السيد:", font=("Arial", 12)).grid(row=4, column=1, sticky="e", pady=5, padx=5)
        edit_payee_var = tk.StringVar(value=record.get("payee", ""))
        tk.Entry(fields_frame, font=("Arial", 12), width=30, textvariable=edit_payee_var, justify="right").grid(row=4, column=0, pady=5, padx=5, sticky="e")

        tk.Label(fields_frame, text="وذلك لقاء:", font=("Arial", 12)).grid(row=5, column=1, sticky="e", pady=5, padx=5)
        edit_reason_var = tk.StringVar(value=record.get("reason", ""))
        tk.Entry(fields_frame, font=("Arial", 12), width=30, textvariable=edit_reason_var, justify="right").grid(row=5, column=0, pady=5, padx=5, sticky="e")

        edit_reconcile_var = tk.BooleanVar(value=record.get("needs_reconciliation", False))
        reconcile_frame = tk.Frame(fields_frame, bg="#fff9c4", padx=10, pady=5)
        reconcile_frame.grid(row=6, column=0, columnspan=2, pady=5, sticky="ew")
        tk.Checkbutton(reconcile_frame, text=" ترصيد (يؤثر على الصندوق - للتجميع في قائمة الترصيد)",
                       variable=edit_reconcile_var, font=("Arial", 11, "bold"),
                       bg="#fff9c4", fg="#f57f17").pack(side=tk.RIGHT, padx=10)

        exchange_frame = tk.Frame(edit_window, bg="#f0f0f0", padx=15, pady=10)
        tk.Label(exchange_frame, text="بيانات التصريف", font=("Arial", 12, "bold"), bg="#f0f0f0").grid(row=0, column=0, columnspan=2, pady=5)

        tk.Label(exchange_frame, text="نوع العملية:", font=("Arial", 11), bg="#f0f0f0").grid(row=1, column=1, sticky="e", pady=3, padx=5)
        edit_exchange_type_var = tk.StringVar(value=record.get("exchange_type", "بيع"))
        ex_type_frame = tk.Frame(exchange_frame, bg="#f0f0f0")
        ex_type_frame.grid(row=1, column=0, sticky="w")

        tk.Radiobutton(ex_type_frame, text="بيع", variable=edit_exchange_type_var, value="بيع", font=("Arial", 10), bg="#f0f0f0").pack(side=tk.RIGHT, padx=3)
        tk.Radiobutton(ex_type_frame, text="شراء", variable=edit_exchange_type_var, value="شراء", font=("Arial", 10), bg="#f0f0f0").pack(side=tk.RIGHT, padx=3)
        tk.Radiobutton(ex_type_frame, text="يورو→دولار", variable=edit_exchange_type_var, value="يورو_دولار", font=("Arial", 10), bg="#f0f0f0").pack(side=tk.RIGHT, padx=3)
        tk.Radiobutton(ex_type_frame, text="دولار→يورو", variable=edit_exchange_type_var, value="دولار_يورو", font=("Arial", 10), bg="#f0f0f0").pack(side=tk.RIGHT, padx=3)

        tk.Label(exchange_frame, text="سعر الصرف:", font=("Arial", 11), bg="#f0f0f0").grid(row=2, column=1, sticky="e", pady=3, padx=5)
        edit_exchange_rate_var = tk.StringVar(value=record.get("exchange_rate", ""))
        tk.Entry(exchange_frame, font=("Arial", 12), width=15, textvariable=edit_exchange_rate_var, justify="right").grid(row=2, column=0, pady=3, padx=5, sticky="e")

        tk.Label(exchange_frame, text="المبلغ المراد تصريفه:", font=("Arial", 11), bg="#f0f0f0").grid(row=3, column=1, sticky="e", pady=3, padx=5)
        edit_exchange_amount_var = tk.StringVar(value=record.get("exchange_amount", ""))
        tk.Entry(exchange_frame, font=("Arial", 12), width=15, textvariable=edit_exchange_amount_var, justify="right").grid(row=3, column=0, pady=3, padx=5, sticky="e")

        tk.Label(exchange_frame, text="المبلغ الناتج:", font=("Arial", 11), bg="#f0f0f0").grid(row=4, column=1, sticky="e", pady=3, padx=5)
        edit_exchange_result_var = tk.StringVar(value=record.get("exchange_result", ""))
        tk.Entry(exchange_frame, font=("Arial", 12), width=15, textvariable=edit_exchange_result_var, justify="right").grid(row=4, column=0, pady=3, padx=5, sticky="e")

        def toggle_exchange_fields(*args):
            if edit_type_var.get() == "تصريف":
                exchange_frame.pack(fill=tk.X, padx=20, pady=5)
            else:
                exchange_frame.pack_forget()

        edit_type_var.trace_add("write", toggle_exchange_fields)
        toggle_exchange_fields()

        btn_frame = tk.Frame(edit_window)
        btn_frame.pack(pady=15)

        def save_edit():
            self.create_backup(f"تعديل سند رقم {record.get('id')}")

            updated_record = record.copy()
            updated_record["type"] = edit_type_var.get()
            updated_record["amount"] = edit_amount_var.get()
            updated_record["currency"] = edit_currency_var.get()
            updated_record["amount_words"] = edit_amount_words_var.get()
            updated_record["treasurer"] = edit_treasurer_var.get()
            updated_record["payee"] = edit_payee_var.get()
            updated_record["reason"] = edit_reason_var.get()
            updated_record["needs_reconciliation"] = edit_reconcile_var.get()
            updated_record["edited"] = True
            updated_record["edited_datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if edit_type_var.get() == "تصريف":
                updated_record["exchange_type"] = edit_exchange_type_var.get()
                updated_record["exchange_rate"] = edit_exchange_rate_var.get()
                updated_record["exchange_amount"] = edit_exchange_amount_var.get()
                updated_record["exchange_result"] = edit_exchange_result_var.get()

                result_num = extract_number_from_text(updated_record["exchange_result"])
                impact = self.calculate_exchange_impact(
                    updated_record["exchange_type"],
                    updated_record["exchange_amount"],
                    result_num,
                    updated_record["currency"]
                )
                updated_record["impact_SYP"] = impact["ل.س"]
                updated_record["impact_USD"] = impact["$"]
                updated_record["impact_EUR"] = impact["€"]

            if not edit_reconcile_var.get():
                self.reverse_record_impact(original_record)
                self.apply_record_impact(updated_record)

            self.records[record_index] = updated_record
            self.save_records()

            try:
                file_path = updated_record.get("file_path", "")
                if file_path and os.path.exists(file_path):
                    self.regenerate_pdf(updated_record, file_path)
            except:
                pass

            self.update_balance_display()
            messagebox.showinfo("نجاح", f"تم تعديل السند رقم {record.get('id')} بنجاح")
            edit_window.destroy()

        tk.Button(btn_frame, text="حفظ التعديلات", command=save_edit, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="إلغاء", command=edit_window.destroy, bg="#757575", fg="white", font=("Arial", 11), width=10).pack(side=tk.LEFT, padx=5)

    def regenerate_pdf(self, record, file_path):
        font_name = 'Helvetica'
        if FONT_PATH and os.path.exists(FONT_PATH):
            pdfmetrics.registerFont(TTFont('WinFont', FONT_PATH))
            font_name = 'WinFont'

        c = canvas.Canvas(file_path, pagesize=A6)
        width, height = A6

        order_type = record.get("type", "صرف")
        currency = record.get("currency", "ل.س")

        c.setFont(font_name, 20)
        title = f"سند {order_type}"
        c.drawCentredString(width/2, height - 40, reshape_text(title))

        c.setFont(font_name, 12)
        c.rect(width/2 - 40, height - 75, 80, 25)
        c.drawCentredString(width/2, height - 70, record.get("amount", ""))

        if currency == "ل.س":
            currency_text = reshape_text(currency)
        else:
            currency_text = currency

        c.drawRightString(width/2 - 45, height - 70, currency_text)

        c.setFillColorRGB(0.8, 0, 0)
        c.drawRightString(width - 30, height - 70, record.get("id", ""))
        c.setFillColorRGB(0, 0, 0)

        c.setLineWidth(0.5)
        c.line(20, height - 85, width - 20, height - 85)

        y_start = height - 120
        line_spacing = 40
        label_x = width - 30
        line_end_x = 30

        if order_type == "صرف":
            payee_label = "إلى السيد :"
            action_text = "الرجاء صرف المبلغ المحرر أعلاه وقدره :"
        elif order_type == "قبض":
            payee_label = "من السيد :"
            action_text = "الرجاء قبض المبلغ المحرر أعلاه وقدره :"
        else:
            ex_type = record.get("exchange_type", "بيع")
            payee_label = "من/إلى السيد :"
            if ex_type == "بيع":
                action_text = "تصريف (بيع) المبلغ المحرر أعلاه وقدره :"
            elif ex_type == "شراء":
                action_text = "تصريف (شراء) المبلغ المحرر أعلاه وقدره :"
            elif ex_type == "يورو_دولار":
                action_text = "تصريف (يورو → دولار) المبلغ المحرر أعلاه وقدره :"
            elif ex_type == "دولار_يورو":
                action_text = "تصريف (دولار → يورو) المبلغ المحرر أعلاه وقدره :"

        fields = [
            ("إلى أمين الصندوق :", record.get("treasurer", "")),
            (action_text, record.get("amount", "") + " " + currency),
            ("المبلغ كتابة :", record.get("amount_words", "")),
            (payee_label, record.get("payee", "")),
            ("وذلك لقاء :", record.get("reason", ""))
        ]

        if order_type == "تصريف":
            fields.append((f"سعر الصرف :", record.get("exchange_rate", "")))
            fields.append((f"المبلغ المراد تصريفه :", record.get("exchange_amount", "")))
            fields.append((f"المبلغ الناتج :", record.get("exchange_result", "")))

        c.setFont(font_name, 11)
        for i, (label, value) in enumerate(fields):
            y = y_start - (i * line_spacing)
            label_reshaped = reshape_text(label)
            label_width = c.stringWidth(label_reshaped, font_name, 11)

            c.drawRightString(label_x, y, label_reshaped)

            c.setDash(1, 2)
            c.line(line_end_x, y - 5, label_x - label_width - 5, y - 5)
            c.setDash()

            c.drawRightString(label_x - label_width - 10, y, reshape_text(str(value)))

        y_bottom = y_start - (len(fields) * line_spacing) + 10

        c.setFont(font_name, 11)
        c.drawRightString(width - 30, y_bottom, reshape_text("التاريخ"))
        c.drawCentredString(50, y_bottom, reshape_text("المحاسب"))

        c.save()

    def create_backup(self, operation_type="حفظ سند"):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder = os.path.join(self.backup_dir, f"Backup_{timestamp}")
            os.makedirs(backup_folder, exist_ok=True)

            files_to_backup = [
                (self.records_file, "sarf_app_records.json"),
                (self.balance_file, "sarf_app_balance.json"),
                (self.opening_balance_file, "sarf_app_opening_balance.json"),
                (self.sarf_id_file, "sarf_app_last_sarf_id.txt"),
                (self.qabd_id_file, "sarf_app_last_qabd_id.txt"),
                (self.tasreef_id_file, "sarf_app_last_tasreef_id.txt")
            ]

            copied_count = 0
            for src_file, dest_name in files_to_backup:
                if os.path.exists(src_file):
                    dest_file = os.path.join(backup_folder, dest_name)
                    shutil.copy2(src_file, dest_file)
                    copied_count += 1

            info_file = os.path.join(backup_folder, "backup_info.txt")
            with open(info_file, "w", encoding="utf-8") as f:
                f.write(f"نسخة احتياطية تلقائية\n")
                f.write(f"التاريخ والوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"نوع العملية: {operation_type}\n")
                f.write(f"عدد الملفات المنسوخة: {copied_count}\n")
                f.write(f"رصيد الليرة: {format_number(self.balance['ل.س'])}\n")
                f.write(f"رصيد الدولار: {format_number(self.balance['$'])}\n")
                f.write(f"رصيد اليورو: {format_number(self.balance['€'])}\n")
                f.write(f"عدد السندات المسجلة: {len(self.records)}\n")

            return True
        except Exception as e:
            print(f"⚠️ فشل إنشاء النسخة الاحتياطية: {str(e)}")
            return False

    def restore_backup(self):
        if not os.path.exists(self.backup_dir):
            messagebox.showinfo("معلومات", "لا توجد نسخ احتياطية متاحة.")
            return

        backup_folders = [f for f in os.listdir(self.backup_dir) if f.startswith("Backup_")]
        if not backup_folders:
            messagebox.showinfo("معلومات", "لا توجد نسخ احتياطية متاحة.")
            return

        backup_folders.sort(reverse=True)

        restore_window = tk.Toplevel(self.root)
        restore_window.title("استرجاع نسخة احتياطية")
        restore_window.geometry("500x400")
        restore_window.resizable(False, False)

        tk.Label(restore_window, text="اختر النسخة الاحتياطية المراد استرجاعها", font=("Arial", 14, "bold")).pack(pady=10)

        list_frame = tk.Frame(restore_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        backup_list = tk.Listbox(list_frame, font=("Arial", 10), yscrollcommand=scrollbar.set, height=10)
        backup_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=backup_list.yview)

        for folder in backup_folders:
            backup_list.insert(tk.END, folder.replace("Backup_", ""))

        def do_restore():
            selection = backup_list.curselection()
            if not selection:
                messagebox.showwarning("تحذير", "يرجى اختيار نسخة احتياطية أولاً.")
                return

            selected_folder = backup_folders[selection[0]]
            backup_path = os.path.join(self.backup_dir, selected_folder)

            if messagebox.askyesno("تأكيد", f"هل أنت متأكد من استرجاع النسخة الاحتياطية:\n{selected_folder}\n\nسيتم استبدال البيانات الحالية!"):
                try:
                    files_map = {
                        "sarf_app_records.json": self.records_file,
                        "sarf_app_balance.json": self.balance_file,
                        "sarf_app_opening_balance.json": self.opening_balance_file,
                        "sarf_app_last_sarf_id.txt": self.sarf_id_file,
                        "sarf_app_last_qabd_id.txt": self.qabd_id_file,
                        "sarf_app_last_tasreef_id.txt": self.tasreef_id_file
                    }

                    for src_name, dest_file in files_map.items():
                        src_file = os.path.join(backup_path, src_name)
                        if os.path.exists(src_file):
                            shutil.copy2(src_file, dest_file)

                    self.records = self.load_records()
                    self.balance = self.load_balance()
                    self.opening_balance = self.check_new_day()
                    self.update_balance_display()
                    self.update_id_display()

                    messagebox.showinfo("نجاح", f"تم استرجاع النسخة الاحتياطية بنجاح!\n{selected_folder}")
                    restore_window.destroy()

                except Exception as e:
                    messagebox.showerror("خطأ", f"فشل استرجاع النسخة الاحتياطية: {str(e)}")

        tk.Button(restore_window, text="استرجاع النسخة المحددة", command=do_restore, bg="#9C27B0", fg="white", font=("Arial", 12, "bold"), width=20).pack(pady=10)
        tk.Button(restore_window, text="إلغاء", command=restore_window.destroy, bg="#757575", fg="white", font=("Arial", 10), width=15).pack(pady=5)

    def load_balance(self):
        if os.path.exists(self.balance_file):
            try:
                with open(self.balance_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return self.default_balance.copy()

    def save_balance(self):
        try:
            with open(self.balance_file, "w", encoding="utf-8") as f:
                json.dump(self.balance, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load_opening_balance(self):
        if os.path.exists(self.opening_balance_file):
            try:
                with open(self.opening_balance_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {"date": "", "ل.س": 0, "$": 0, "€": 0}

    def save_opening_balance(self, balance):
        try:
            with open(self.opening_balance_file, "w", encoding="utf-8") as f:
                json.dump(balance, f, ensure_ascii=False, indent=2)
        except:
            pass

    def check_new_day(self):
        today = datetime.now().strftime("%Y-%m-%d")
        opening = self.load_opening_balance()

        if not opening or opening.get("date") != today:
            opening = {
                "date": today,
                "ل.س": self.balance["ل.س"],
                "$": self.balance["$"],
                "€": self.balance["€"]
            }
            self.save_opening_balance(opening)

        return opening

    def update_balance_display(self):
        self.balance_syp_var.set(format_number(self.balance["ل.س"]))
        self.balance_usd_var.set(format_number(self.balance["$"]))
        self.balance_eur_var.set(format_number(self.balance["€"]))

    def calculate_exchange_impact(self, ex_type, amount, result, currency):
        impact = {"ل.س": 0, "$": 0, "€": 0}
        try:
            amount = float(amount)
            result = float(result)
        except:
            return impact

        if ex_type == "بيع":
            if currency == "€":
                impact["€"] = -amount
            else:
                impact["$"] = -amount
            impact["ل.س"] = +result
        elif ex_type == "شراء":
            impact["ل.س"] = -amount
            if currency == "€":
                impact["€"] = +result
            else:
                impact["$"] = +result
        elif ex_type == "يورو_دولار":
            impact["€"] = -amount
            impact["$"] = +result
        elif ex_type == "دولار_يورو":
            impact["$"] = -amount
            impact["€"] = +result

        return impact

    def update_exchange_impact_display(self):
        ex_type = self.exchange_type_var.get()
        amount = self.exchange_amount_var.get()
        result_text = self.exchange_result_var.get()
        currency = self.currency_var.get()

        result = extract_number_from_text(result_text)
        impact = self.calculate_exchange_impact(ex_type, amount, result, currency)

        def format_impact(val, symbol):
            if val > 0:
                return f"{symbol}: +{format_number(val)}"
            elif val < 0:
                return f"{symbol}: {format_number(val)}"
            else:
                return f"{symbol}: 0.00"

        self.impact_syp_var.set(format_impact(impact["ل.س"], "ل.س"))
        self.impact_usd_var.set(format_impact(impact["$"], "$"))
        self.impact_eur_var.set(format_impact(impact["€"], "€"))

    def update_balance(self, order_type, amount, currency, exchange_info=None, needs_reconciliation=False):
        try:
            amount = float(amount)
        except:
            return

        balance_before = self.balance.copy()

        if order_type == "قبض":
            self.balance[currency] = self.balance.get(currency, 0) + amount
        elif order_type == "صرف":
            self.balance[currency] = self.balance.get(currency, 0) - amount
        elif order_type == "تصريف" and exchange_info:
            ex_type = exchange_info.get("type")
            ex_amount = float(exchange_info.get("amount", 0))
            ex_result = extract_number_from_text(exchange_info.get("result", "0"))

            impact = self.calculate_exchange_impact(ex_type, ex_amount, ex_result, currency)

            self.balance["ل.س"] = self.balance.get("ل.س", 0) + impact["ل.س"]
            self.balance["$"] = self.balance.get("$", 0) + impact["$"]
            self.balance["€"] = self.balance.get("€", 0) + impact["€"]

        self.save_balance()
        self.update_balance_display()

        return balance_before

    def manual_balance_adjust(self):
        adjust_window = tk.Toplevel(self.root)
        adjust_window.title("ضبط رصيد الصندوق")
        adjust_window.geometry("400x300")
        adjust_window.resizable(False, False)

        tk.Label(adjust_window, text="ضبط رصيد الصندوق يدوياً", font=("Arial", 14, "bold")).pack(pady=10)

        frame = tk.Frame(adjust_window, padx=20, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="ليرة سورية:", font=("Arial", 11)).grid(row=0, column=0, sticky="e", pady=5)
        syp_entry = tk.Entry(frame, font=("Arial", 12), width=15, justify="right")
        syp_entry.insert(0, format_number(self.balance["ل.س"]))
        syp_entry.grid(row=0, column=1, pady=5)

        tk.Label(frame, text="دولار:", font=("Arial", 11)).grid(row=1, column=0, sticky="e", pady=5)
        usd_entry = tk.Entry(frame, font=("Arial", 12), width=15, justify="right")
        usd_entry.insert(0, format_number(self.balance["$"]))
        usd_entry.grid(row=1, column=1, pady=5)

        tk.Label(frame, text="يورو:", font=("Arial", 11)).grid(row=2, column=0, sticky="e", pady=5)
        eur_entry = tk.Entry(frame, font=("Arial", 12), width=15, justify="right")
        eur_entry.insert(0, format_number(self.balance["€"]))
        eur_entry.grid(row=2, column=1, pady=5)

        def save_adjust():
            try:
                syp_val = float(syp_entry.get().replace(",", ""))
                usd_val = float(usd_entry.get().replace(",", ""))
                eur_val = float(eur_entry.get().replace(",", ""))

                if syp_val < 0 or usd_val < 0 or eur_val < 0:
                    messagebox.showerror("خطأ", "لا يمكن أن يكون الرصيد سالباً!\nيرجى إدخال قيم موجبة فقط.")
                    return

                self.balance["ل.س"] = syp_val
                self.balance["$"] = usd_val
                self.balance["€"] = eur_val
                self.save_balance()
                self.update_balance_display()
                self.create_backup("ضبط يدوي للرصيد")
                messagebox.showinfo("نجاح", "تم ضبط الرصيد بنجاح وإنشاء نسخة احتياطية")
                adjust_window.destroy()
            except:
                messagebox.showerror("خطأ", "يرجى إدخال أرقام صحيحة")

        tk.Button(adjust_window, text="حفظ", command=save_adjust, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), width=10).pack(pady=10)

    def load_records(self):
        if os.path.exists(self.records_file):
            try:
                with open(self.records_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_records(self):
        try:
            with open(self.records_file, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except:
            pass

    def check_duplicate(self, order_type, amount, payee, reason):
        for rec in self.records:
            if rec.get("deleted"):
                continue
            if (rec.get("type") == order_type and
                rec.get("amount") == amount and
                rec.get("payee") == payee and
                rec.get("reason") == reason):
                return True
        return False

    def add_record(self, record):
        self.records.append(record)
        self.save_records()

    def get_id_file(self, order_type):
        if order_type == "صرف":
            return self.sarf_id_file
        elif order_type == "قبض":
            return self.qabd_id_file
        else:
            return self.tasreef_id_file

    def get_default_id(self, order_type):
        if order_type == "صرف":
            return self.default_sarf_id
        elif order_type == "قبض":
            return self.default_qabd_id
        else:
            return self.default_tasreef_id

    def load_id(self, order_type):
        id_file = self.get_id_file(order_type)
        default_id = self.get_default_id(order_type)
        if os.path.exists(id_file):
            try:
                with open(id_file, "r") as f:
                    return int(f.read().strip())
            except:
                return default_id
        return default_id

    def save_id(self, new_id, order_type):
        id_file = self.get_id_file(order_type)
        try:
            with open(id_file, "w") as f:
                f.write(str(new_id))
        except:
            pass

    def get_current_id(self):
        order_type = self.order_type_var.get()
        return self.load_id(order_type)

    def update_id_display(self):
        current_id = self.get_current_id()
        self.entries["id"].config(state='normal')
        self.entries["id"].delete(0, tk.END)
        self.entries["id"].insert(0, f"{current_id:04d}")
        self.entries["id"].config(state='readonly')

    def on_order_type_change(self, *args):
        self.on_type_change()

    def on_type_change(self):
        order_type = self.order_type_var.get()
        if order_type == "تصريف":
            self.exchange_frame.grid()
            self.exchange_impact_frame.grid()
        else:
            self.exchange_frame.grid_remove()
            self.exchange_impact_frame.grid_remove()
        self.update_id_display()

    def calculate_exchange(self, *args):
        try:
            rate = float(self.exchange_rate_var.get())
            amount = float(self.exchange_amount_var.get())
            ex_type = self.exchange_type_var.get()
            currency = self.currency_var.get()

            if ex_type == "بيع":
                result = amount * rate
                self.exchange_result_var.set(f"{result:,.2f} ل.س")
            elif ex_type == "شراء":
                result = amount / rate
                symbol = "€" if currency == "€" else "$"
                self.exchange_result_var.set(f"{result:,.2f} {symbol}")
            elif ex_type == "يورو_دولار":
                result = amount * rate
                self.exchange_result_var.set(f"{result:,.2f} $")
            elif ex_type == "دولار_يورو":
                result = amount * rate
                self.exchange_result_var.set(f"{result:,.2f} €")

            self.update_exchange_impact_display()
        except:
            self.exchange_result_var.set("0")
            self.impact_syp_var.set("ل.س: 0.00")
            self.impact_usd_var.set("$: 0.00")
            self.impact_eur_var.set("€: 0.00")

    def reset_id(self):
        order_type = self.order_type_var.get()
        default_id = self.get_default_id(order_type)
        if messagebox.askyesno("تأكيد", f"هل تريد فعلاً إعادة عداد سند {order_type} إلى {default_id:04d}؟"):
            self.save_id(default_id, order_type)
            self.update_id_display()
            self.create_backup("تصفير العداد")

    def get_today_folder(self):
        today = datetime.now().strftime("%Y-%m-%d")
        folder_path = os.path.join(self.app_dir, "Reports", today)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def open_query_window(self):
        query_window = tk.Toplevel(self.root)
        query_window.title("استعلام عن السندات")
        query_window.geometry("600x500")
        query_window.resizable(True, True)

        tk.Label(query_window, text="استعلام عن السندات", font=("Arial", 16, "bold")).pack(pady=10)

        filter_frame = tk.Frame(query_window, padx=10, pady=10)
        filter_frame.pack(fill=tk.X, padx=10)

        tk.Label(filter_frame, text="من تاريخ:", font=("Arial", 11)).grid(row=0, column=0, sticky="e", pady=5, padx=5)
        self.query_date_from = tk.Entry(filter_frame, font=("Arial", 11), width=15)
        self.query_date_from.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.query_date_from.grid(row=0, column=1, pady=5, padx=5)

        tk.Label(filter_frame, text="إلى تاريخ:", font=("Arial", 11)).grid(row=1, column=0, sticky="e", pady=5, padx=5)
        self.query_date_to = tk.Entry(filter_frame, font=("Arial", 11), width=15)
        self.query_date_to.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.query_date_to.grid(row=1, column=1, pady=5, padx=5)

        tk.Label(filter_frame, text="اسم حامل السند:", font=("Arial", 11)).grid(row=2, column=0, sticky="e", pady=5, padx=5)
        self.query_payee = tk.Entry(filter_frame, font=("Arial", 11), width=30)
        self.query_payee.grid(row=2, column=1, columnspan=2, pady=5, padx=5, sticky="w")

        tk.Label(filter_frame, text="بيان السند:", font=("Arial", 11)).grid(row=3, column=0, sticky="e", pady=5, padx=5)
        self.query_reason = tk.Entry(filter_frame, font=("Arial", 11), width=30)
        self.query_reason.grid(row=3, column=1, columnspan=2, pady=5, padx=5, sticky="w")

        tk.Label(filter_frame, text="نوع السند:", font=("Arial", 11)).grid(row=4, column=0, sticky="e", pady=5, padx=5)
        self.query_type = ttk.Combobox(filter_frame, values=["الكل", "صرف", "قبض", "تصريف"], state="readonly", width=28)
        self.query_type.set("الكل")
        self.query_type.grid(row=4, column=1, columnspan=2, pady=5, padx=5, sticky="w")

        btn_frame = tk.Frame(query_window)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="بحث", command=lambda: self.execute_query(query_window), bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="إلغاء", command=query_window.destroy, bg="#757575", fg="white", font=("Arial", 11), width=10).pack(side=tk.LEFT, padx=5)

    def execute_query(self, query_window):
        date_from = self.query_date_from.get().strip()
        date_to = self.query_date_to.get().strip()
        payee = self.query_payee.get().strip()
        reason = self.query_reason.get().strip()
        doc_type = self.query_type.get()

        filtered_records = []
        for rec in self.records:
            rec_date = rec.get("date", "")
            if date_from and rec_date < date_from:
                continue
            if date_to and rec_date > date_to:
                continue
            if payee and payee.lower() not in rec.get("payee", "").lower():
                continue
            if reason and reason.lower() not in rec.get("reason", "").lower():
                continue
            if doc_type != "الكل" and rec.get("type") != doc_type:
                continue
            filtered_records.append(rec)

        if not filtered_records:
            messagebox.showinfo("نتيجة البحث", "لا توجد نتائج مطابقة للبحث.")
            return

        today_folder = self.get_today_folder()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(today_folder, f"Query_Report_{timestamp}.pdf")

        try:
            font_name = 'Helvetica'
            if FONT_PATH and os.path.exists(FONT_PATH):
                pdfmetrics.registerFont(TTFont('WinFont', FONT_PATH))
                font_name = 'WinFont'

            c = canvas.Canvas(report_path, pagesize=A4)
            width, height = A4

            title_size = self.settings["fonts"]["title_size"]
            body_size = self.settings["fonts"]["body_size"]
            margins = self.settings["margins"]
            col_widths = self.settings["query_report"]["col_widths"]
            row_height = self.settings["table"]["row_height"]
            text_align = self.settings["query_report"].get("text_align", "center")
            header_align = self.settings["query_report"].get("header_align", "center")

            header_bg = hex_to_reportlab_color(self.settings["colors"]["table_header_bg"])
            header_text = hex_to_reportlab_color(self.settings["colors"]["table_header_text"])
            deleted_bg = hex_to_reportlab_color(self.settings["colors"]["row_deleted_bg"])
            deleted_text = hex_to_reportlab_color(self.settings["colors"]["row_deleted_text"])
            edited_bg = hex_to_reportlab_color(self.settings["colors"]["row_edited_bg"])
            edited_text = hex_to_reportlab_color(self.settings["colors"]["row_edited_text"])
            pending_bg = hex_to_reportlab_color(self.settings["colors"]["row_pending_bg"])
            pending_text = hex_to_reportlab_color(self.settings["colors"]["row_pending_text"])
            reconciled_bg = hex_to_reportlab_color(self.settings["colors"]["row_reconciled_bg"])
            reconciled_text = hex_to_reportlab_color(self.settings["colors"]["row_reconciled_text"])

            c.setFont(font_name, title_size)
            c.drawCentredString(width/2, height - margins["top"], reshape_text("تقرير الاستعلام"))

            c.setFont(font_name, 10)
            c.drawString(margins["left"], height - margins["top"] - 30, f"من تاريخ: {date_from}")
            c.drawString(250, height - margins["top"] - 30, f"إلى تاريخ: {date_to}")

            y_info = height - margins["top"] - 45
            if payee:
                c.drawString(margins["left"], y_info, f"حامل السند: {payee}")
                y_info -= 15
            if reason:
                c.drawString(margins["left"], y_info, f"البيان: {reason}")
                y_info -= 15
            if doc_type != "الكل":
                c.drawString(margins["left"], y_info, f"النوع: {doc_type}")
                y_info -= 15

            c.drawString(margins["left"], y_info - 15, f"عدد النتائج: {len(filtered_records)}")

            y = height - margins["top"] - 120

            # تحويل المحاذاة النصية إلى قيم ReportLab
            align_map = {'center': 'CENTER', 'right': 'RIGHT', 'left': 'LEFT'}
            ta = align_map.get(text_align, 'CENTER')
            ha = align_map.get(header_align, 'CENTER')

            # تحضير بيانات الجدول باستخدام LongTable
            headers = [reshape_text("الحالة"), reshape_text("النوع"), reshape_text("الرقم"), reshape_text("التاريخ"), reshape_text("المبلغ"), reshape_text("حامل السند"), reshape_text("البيان")]
            table_data = [headers]

            for rec in filtered_records:
                is_deleted = rec.get("deleted", False)
                is_edited = rec.get("edited", False)
                needs_recon = rec.get("needs_reconciliation", False)
                is_reconciled = rec.get("reconciled", False)

                if is_deleted:
                    status_text = reshape_text("محذوف")
                elif is_edited:
                    status_text = reshape_text("معدل")
                elif needs_recon and not is_reconciled:
                    status_text = reshape_text("بانتظار الترصيد")
                elif needs_recon and is_reconciled:
                    status_text = reshape_text("تم الترصيد")
                else:
                    status_text = reshape_text("نشط")

                # استخدام فقرات للنصوص الطويلة خاصة في عمود البيان
                row_data = [
                    status_text,
                    reshape_text(rec.get("type", "")),
                    reshape_text(rec.get("id", "")),
                    reshape_text(rec.get("date", "")),
                    reshape_text(rec.get("amount", "") + " " + rec.get("currency", "")),
                    make_arabic_paragraph(rec.get("payee", ""), font_name, body_size, ta, line_spacing),
                    make_arabic_paragraph(rec.get("reason", ""), font_name, body_size, ta, line_spacing)
                ]
                table_data.append(row_data)

            # إنشاء الجدول باستخدام LongTable
            t = LongTable(table_data, colWidths=col_widths)

            # بناء التنسيقات ديناميكياً
            style_commands = [
                # الشبكة والحدود
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), header_bg),
                ('TEXTCOLOR', (0, 0), (-1, 0), header_text),
                
                # المحاذاة
                ('ALIGN', (0, 0), (-1, 0), ha),
                ('ALIGN', (0, 1), (-1, -1), ta),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # الخطوط
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, 0), body_size),
                ('FONTNAME', (0, 1), (-1, -1), font_name),
                ('FONTSIZE', (0, 1), (-1, -1), body_size),
                
                # الحشو الداخلي
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                
                # تباعد الأسطر
                ('LEADING', (0, 0), (-1, -1), body_size * 1.2),
            ]

            # إضافة ألوان الصفوف بناءً على الحالة
            for i, rec in enumerate(filtered_records):
                row_idx = i + 1  # +1 لأن الصف 0 هو الرأس
                is_deleted = rec.get("deleted", False)
                is_edited = rec.get("edited", False)
                needs_recon = rec.get("needs_reconciliation", False)
                is_reconciled = rec.get("reconciled", False)

                if is_deleted:
                    style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), deleted_bg))
                    style_commands.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), deleted_text))
                elif is_edited:
                    style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), edited_bg))
                    style_commands.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), edited_text))
                elif needs_recon and not is_reconciled:
                    style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), pending_bg))
                    style_commands.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), pending_text))
                elif needs_recon and is_reconciled:
                    style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), reconciled_bg))
                    style_commands.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), reconciled_text))

            t.setStyle(TableStyle(style_commands))

            # حساب المساحة المتاحة ورسم الجدول
            available_height = y - 50
            t.wrapOn(c, width - margins["left"] - margins["right"], available_height)
            
            # التحقق مما إذا كان الجدول يحتاج لصفحات متعددة
            table_height = t._height
            current_y = y
            
            # رسم الجدول
            t.drawOn(c, margins["left"], current_y - table_height)

            c.save()

            if sys.platform == "win32":
                os.startfile(report_path)
            elif sys.platform == "darwin":
                subprocess.call(["open", report_path])
            else:
                subprocess.call(["xdg-open", report_path])

            messagebox.showinfo("نجاح", f"تم إنشاء تقرير الاستعلام\nعدد النتائج: {len(filtered_records)}\nالمسار: {report_path}")

        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء إنشاء التقرير: {str(e)}")

    def generate_pdf(self, file_path):
        data = {k: e.get() for k, e in self.entries.items()}
        order_type = self.order_type_var.get()
        current_id = self.get_current_id()
        data["id"] = f"{current_id:04d}"
        currency = self.currency_var.get()

        font_name = 'Helvetica'
        if FONT_PATH and os.path.exists(FONT_PATH):
            pdfmetrics.registerFont(TTFont('WinFont', FONT_PATH))
            font_name = 'WinFont'

        c = canvas.Canvas(file_path, pagesize=A6)
        width, height = A6

        c.setFont(font_name, 20)
        title = f"سند {order_type}"
        c.drawCentredString(width/2, height - 40, reshape_text(title))

        c.setFont(font_name, 12)
        c.rect(width/2 - 40, height - 75, 80, 25)
        c.drawCentredString(width/2, height - 70, data["amount"])

        if currency == "ل.س":
            currency_text = reshape_text(currency)
        else:
            currency_text = currency

        c.drawRightString(width/2 - 45, height - 70, currency_text)

        c.setFillColorRGB(0.8, 0, 0)
        c.drawRightString(width - 30, height - 70, data["id"])
        c.setFillColorRGB(0, 0, 0)

        c.setLineWidth(0.5)
        c.line(20, height - 85, width - 20, height - 85)

        y_start = height - 120
        line_spacing = 40
        label_x = width - 30
        line_end_x = 30

        if order_type == "صرف":
            payee_label = "إلى السيد :"
            action_text = "الرجاء صرف المبلغ المحرر أعلاه وقدره :"
        elif order_type == "قبض":
            payee_label = "من السيد :"
            action_text = "الرجاء قبض المبلغ المحرر أعلاه وقدره :"
        else:
            ex_type = self.exchange_type_var.get()
            payee_label = "من/إلى السيد :"
            if ex_type == "بيع":
                action_text = "تصريف (بيع) المبلغ المحرر أعلاه وقدره :"
            elif ex_type == "شراء":
                action_text = "تصريف (شراء) المبلغ المحرر أعلاه وقدره :"
            elif ex_type == "يورو_دولار":
                action_text = "تصريف (يورو → دولار) المبلغ المحرر أعلاه وقدره :"
            elif ex_type == "دولار_يورو":
                action_text = "تصريف (دولار → يورو) المبلغ المحرر أعلاه وقدره :"

        fields = [
            ("إلى أمين الصندوق :", data["treasurer"]),
            (action_text, data["amount"] + " " + currency),
            ("المبلغ كتابة :", data["amount_words"]),
            (payee_label, data["payee"]),
            ("وذلك لقاء :", data["reason"])
        ]

        if order_type == "تصريف":
            try:
                rate = self.exchange_rate_var.get()
                ex_amount = self.exchange_amount_var.get()
                ex_type = self.exchange_type_var.get()
                result = self.exchange_result_var.get()

                fields.append((f"سعر الصرف :", rate))
                fields.append((f"المبلغ المراد تصريفه :", ex_amount))
                fields.append((f"المبلغ الناتج :", result))

                result_num = extract_number_from_text(result)
                impact = self.calculate_exchange_impact(ex_type, ex_amount, result_num, currency)

                fields.append((f"تأثير ل.س :", f"+{format_number(impact['ل.س'])}" if impact['ل.س'] >= 0 else format_number(impact['ل.س'])))
                fields.append((f"تأثير $ :", f"+{format_number(impact['$'])}" if impact['$'] >= 0 else format_number(impact['$'])))
                fields.append((f"تأثير € :", f"+{format_number(impact['€'])}" if impact['€'] >= 0 else format_number(impact['€'])))
            except:
                pass

        c.setFont(font_name, 11)
        for i, (label, value) in enumerate(fields):
            y = y_start - (i * line_spacing)
            label_reshaped = reshape_text(label)
            label_width = c.stringWidth(label_reshaped, font_name, 11)

            c.drawRightString(label_x, y, label_reshaped)

            c.setDash(1, 2)
            c.line(line_end_x, y - 5, label_x - label_width - 5, y - 5)
            c.setDash()

            c.drawRightString(label_x - label_width - 10, y, reshape_text(value))

        y_bottom = y_start - (len(fields) * line_spacing) + 10

        c.setFont(font_name, 11)
        c.drawRightString(width - 30, y_bottom, reshape_text("التاريخ"))
        c.drawCentredString(50, y_bottom, reshape_text("المحاسب"))

        c.save()

    def save_pdf(self):
        order_type = self.order_type_var.get()
        current_id = self.get_current_id()
        data = {k: e.get() for k, e in self.entries.items()}

        exchange_info = None
        if order_type == "تصريف":
            exchange_info = {
                "type": self.exchange_type_var.get(),
                "rate": self.exchange_rate_var.get(),
                "amount": self.exchange_amount_var.get(),
                "result": self.exchange_result_var.get()
            }

        is_sufficient, error_msg = self.check_sufficient_balance(order_type, data["amount"], self.currency_var.get(),
                                                                  exchange_info if order_type == "تصريف" else None)
        if not is_sufficient:
            if not messagebox.askyesno("تحذير: رصيد غير كافٍ",
                f"{error_msg}\n\nهل تريد المتابعة رغم ذلك؟\n(سيصبح الرصيد سالباً)"):
                return

        if self.check_duplicate(order_type, data["amount"], data["payee"], data["reason"]):
            if not messagebox.askyesno("تحذير", "يوجد سند بنفس المعلومات. هل تريد المتابعة وحفظ نسخة مكررة؟"):
                return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"Snd_{order_type}_{current_id:04d}.pdf"
        )

        if not file_path:
            return

        try:
            self.generate_pdf(file_path)

            needs_reconciliation = self.reconcile_var.get()
            record = {
                "id": f"{current_id:04d}",
                "type": order_type,
                "amount": data["amount"],
                "currency": self.currency_var.get(),
                "payee": data["payee"],
                "treasurer": data["treasurer"],
                "reason": data["reason"],
                "amount_words": data["amount_words"],
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "file_path": file_path,
                "needs_reconciliation": needs_reconciliation,
                "reconciled": False
            }

            if order_type == "تصريف":
                record["exchange_type"] = exchange_info["type"]
                record["exchange_rate"] = exchange_info["rate"]
                record["exchange_amount"] = exchange_info["amount"]
                record["exchange_result"] = exchange_info["result"]

                result_num = extract_number_from_text(exchange_info["result"])
                impact = self.calculate_exchange_impact(
                    exchange_info["type"],
                    exchange_info["amount"],
                    result_num,
                    self.currency_var.get()
                )
                record["impact_SYP"] = impact["ل.س"]
                record["impact_USD"] = impact["$"]
                record["impact_EUR"] = impact["€"]

            balance_before = self.update_balance(order_type, data["amount"], self.currency_var.get(), exchange_info, needs_reconciliation)

            self.add_record(record)

            new_id = current_id + 1
            self.save_id(new_id, order_type)
            self.update_id_display()

            self.create_backup(f"حفظ سند {order_type} رقم {current_id:04d}")

            msg = f"تم حفظ السند بنجاح\nالرقم التسلسلي التالي: {new_id:04d}\n✅ تم إنشاء نسخة احتياطية تلقائياً"
            if needs_reconciliation:
                msg += "\n\n📋 هذا السند سيظهر في قائمة الترصيد للنقل الورقي"

            messagebox.showinfo("نجاح", msg)

        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء الحفظ: {str(e)}")

    def save_and_print(self):
        order_type = self.order_type_var.get()
        current_id = self.get_current_id()
        data = {k: e.get() for k, e in self.entries.items()}

        exchange_info = None
        if order_type == "تصريف":
            exchange_info = {
                "type": self.exchange_type_var.get(),
                "rate": self.exchange_rate_var.get(),
                "amount": self.exchange_amount_var.get(),
                "result": self.exchange_result_var.get()
            }

        is_sufficient, error_msg = self.check_sufficient_balance(order_type, data["amount"], self.currency_var.get(),
                                                                  exchange_info if order_type == "تصريف" else None)
        if not is_sufficient:
            if not messagebox.askyesno("تحذير: رصيد غير كافٍ",
                f"{error_msg}\n\nهل تريد المتابعة رغم ذلك؟\n(سيصبح الرصيد سالباً)"):
                return

        if self.check_duplicate(order_type, data["amount"], data["payee"], data["reason"]):
            if not messagebox.askyesno("تحذير", "يوجد سند بنفس المعلومات. هل تريد المتابعة؟"):
                return

        today_folder = self.get_today_folder()
        file_path = os.path.join(today_folder, f"Snd_{order_type}_{current_id:04d}.pdf")

        try:
            self.generate_pdf(file_path)

            needs_reconciliation = self.reconcile_var.get()
            record = {
                "id": f"{current_id:04d}",
                "type": order_type,
                "amount": data["amount"],
                "currency": self.currency_var.get(),
                "payee": data["payee"],
                "treasurer": data["treasurer"],
                "reason": data["reason"],
                "amount_words": data["amount_words"],
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "file_path": file_path,
                "needs_reconciliation": needs_reconciliation,
                "reconciled": False
            }

            if order_type == "تصريف":
                record["exchange_type"] = exchange_info["type"]
                record["exchange_rate"] = exchange_info["rate"]
                record["exchange_amount"] = exchange_info["amount"]
                record["exchange_result"] = exchange_info["result"]

                result_num = extract_number_from_text(exchange_info["result"])
                impact = self.calculate_exchange_impact(
                    exchange_info["type"],
                    exchange_info["amount"],
                    result_num,
                    self.currency_var.get()
                )
                record["impact_SYP"] = impact["ل.س"]
                record["impact_USD"] = impact["$"]
                record["impact_EUR"] = impact["€"]

            balance_before = self.update_balance(order_type, data["amount"], self.currency_var.get(), exchange_info, needs_reconciliation)

            self.add_record(record)

            new_id = current_id + 1
            self.save_id(new_id, order_type)
            self.update_id_display()

            self.create_backup(f"حفظ وطباعة سند {order_type} رقم {current_id:04d}")

            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.call(["open", file_path])
            else:
                subprocess.call(["xdg-open", file_path])

            msg = f"تم الحفظ في مجلد: {today_folder}\nالرقم التالي: {new_id:04d}\n✅ تم إنشاء نسخة احتياطية تلقائياً"
            if needs_reconciliation:
                msg += "\n\n📋 هذا السند سيظهر في قائمة الترصيد للنقل الورقي"

            messagebox.showinfo("نجاح", msg)

        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ: {str(e)}")

    def generate_daily_report(self):
        today = datetime.now().strftime("%Y-%m-%d")
        today_records = [r for r in self.records if r.get("date") == today]

        today_folder = self.get_today_folder()
        report_path = os.path.join(today_folder, f"Daily_Report_{today}.pdf")

        try:
            font_name = 'Helvetica'
            if FONT_PATH and os.path.exists(FONT_PATH):
                pdfmetrics.registerFont(TTFont('WinFont', FONT_PATH))
                font_name = 'WinFont'

            c = canvas.Canvas(report_path, pagesize=A4)
            width, height = A4

            title_size = self.settings["fonts"]["title_size"]
            header_size = self.settings["fonts"]["header_size"]
            body_size = self.settings["fonts"]["body_size"]

            margins = self.settings["margins"]
            col_widths = self.settings["daily_report"]["col_widths"]
            row_height = self.settings["table"]["row_height"]
            text_align = self.settings["daily_report"].get("text_align", "center")
            header_align = self.settings["daily_report"].get("header_align", "center")
            line_spacing = self.settings["table"].get("line_spacing", 1.2)
            vertical_padding = self.settings["table"].get("vertical_padding", 3)

            header_bg = hex_to_reportlab_color(self.settings["colors"]["table_header_bg"])
            header_text = hex_to_reportlab_color(self.settings["colors"]["table_header_text"])
            deleted_bg = hex_to_reportlab_color(self.settings["colors"]["row_deleted_bg"])
            deleted_text = hex_to_reportlab_color(self.settings["colors"]["row_deleted_text"])
            edited_bg = hex_to_reportlab_color(self.settings["colors"]["row_edited_bg"])
            edited_text = hex_to_reportlab_color(self.settings["colors"]["row_edited_text"])
            pending_bg = hex_to_reportlab_color(self.settings["colors"]["row_pending_bg"])
            pending_text = hex_to_reportlab_color(self.settings["colors"]["row_pending_text"])
            reconciled_bg = hex_to_reportlab_color(self.settings["colors"]["row_reconciled_bg"])
            reconciled_text = hex_to_reportlab_color(self.settings["colors"]["row_reconciled_text"])
            balance_bg = hex_to_reportlab_color(self.settings["colors"]["balance_box_bg"])

            # تحويل المحاذاة النصية إلى قيم ReportLab
            align_map = {'center': 'CENTER', 'right': 'RIGHT', 'left': 'LEFT'}
            ta = align_map.get(text_align, 'CENTER')
            ha = align_map.get(header_align, 'CENTER')

            c.setFont(font_name, title_size)
            c.setFillColor(colors.black)
            c.drawCentredString(width/2, height - margins["top"], reshape_text(f"تقرير يوم {today}"))

            c.setFont(font_name, header_size)
            c.drawString(margins["left"], height - margins["top"] - 30, reshape_text(f"إجمالي السندات: {len(today_records)}"))

            y_start = height - margins["top"] - 80

            # رسم صناديق الافتتاحية والختامية والحركة
            c.setFont(font_name, 14)
            c.setFillColor(colors.Color(0.1, 0.4, 0.1))
            c.drawCentredString(width/2, y_start, reshape_text("حركة الصندوق"))
            c.setFillColor(colors.black)
            y_pos = y_start - 25

            c.setFont(font_name, header_size)
            opening = self.opening_balance

            # افتتاحية الصندوق
            c.setFillColor(balance_bg)
            c.rect(margins["left"], y_pos - 5, width - margins["left"] - margins["right"], 25, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.drawString(margins["left"] + 10, y_pos, reshape_text("افتتاحية الصندوق:"))
            c.drawString(200, y_pos, f"ل.س: {format_number(opening.get('ل.س', 0))}")
            c.drawString(380, y_pos, f"$: {format_number(opening.get('$', 0))}")
            c.drawString(520, y_pos, f"€: {format_number(opening.get('€', 0))}")
            y_pos -= 35

            # ختامية الصندوق
            c.setFillColor(balance_bg)
            c.rect(margins["left"], y_pos - 5, width - margins["left"] - margins["right"], 25, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.drawString(margins["left"] + 10, y_pos, reshape_text("ختامية الصندوق:"))
            c.drawString(200, y_pos, f"ل.س: {format_number(self.balance['ل.س'])}")
            c.drawString(380, y_pos, f"$: {format_number(self.balance['$'])}")
            c.drawString(520, y_pos, f"€: {format_number(self.balance['€'])}")
            y_pos -= 35

            # صافي الحركة
            c.setFillColor(colors.Color(0.95, 0.9, 0.8))
            c.rect(margins["left"], y_pos - 5, width - margins["left"] - margins["right"], 25, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.drawString(margins["left"] + 10, y_pos, reshape_text("صافي الحركة:"))
            syp_diff = self.balance["ل.س"] - opening.get("ل.س", 0)
            usd_diff = self.balance["$"] - opening.get("$", 0)
            eur_diff = self.balance["€"] - opening.get("€", 0)
            c.drawString(200, y_pos, f"ل.س: {format_number(syp_diff)}")
            c.drawString(380, y_pos, f"$: {format_number(usd_diff)}")
            c.drawString(520, y_pos, f"€: {format_number(eur_diff)}")
            y_pos -= 50

            # عنوان تفاصيل السندات
            c.setFont(font_name, 14)
            c.setFillColor(colors.Color(0.1, 0.4, 0.1))
            c.drawCentredString(width/2, y_pos, reshape_text("📋 تفاصيل السندات"))
            c.setFillColor(colors.black)
            y_table_start = y_pos - 30

            # تحضير بيانات الجدول
            headers = [reshape_text("الحالة"), reshape_text("النوع"), reshape_text("الرقم"), reshape_text("المبلغ"), reshape_text("المستلم"), reshape_text("السبب")]
            table_data = [headers]

            for rec in today_records:
                is_deleted = rec.get("deleted", False)
                is_edited = rec.get("edited", False)
                needs_recon = rec.get("needs_reconciliation", False)
                is_reconciled = rec.get("reconciled", False)

                if is_deleted:
                    status_text = reshape_text("محذوف")
                elif is_edited:
                    status_text = reshape_text("معدل")
                elif needs_recon and not is_reconciled:
                    status_text = reshape_text("بانتظار الترصيد")
                elif needs_recon and is_reconciled:
                    status_text = reshape_text("تم الترصيد")
                else:
                    status_text = reshape_text("نشط")

                # استخدام فقرات للنصوص الطويلة خاصة في عمود السبب
                row_data = [
                    status_text,
                    reshape_text(rec.get("type", "")),
                    reshape_text(rec.get("id", "")),
                    reshape_text(rec.get("amount", "") + " " + rec.get("currency", "")),
                    make_arabic_paragraph(rec.get("payee", ""), font_name, body_size, ta, line_spacing),
                    make_arabic_paragraph(rec.get("reason", ""), font_name, body_size, ta, line_spacing)
                ]
                table_data.append(row_data)

            # إنشاء الجدول باستخدام LongTable
            t = LongTable(table_data, colWidths=col_widths)

            # بناء التنسيقات ديناميكياً
            style_commands = [
                # الشبكة والحدود
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), header_bg),
                ('TEXTCOLOR', (0, 0), (-1, 0), header_text),
                
                # المحاذاة
                ('ALIGN', (0, 0), (-1, 0), ha),
                ('ALIGN', (0, 1), (-1, -1), ta),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # الخطوط
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, 0), header_size),
                ('FONTNAME', (0, 1), (-1, -1), font_name),
                ('FONTSIZE', (0, 1), (-1, -1), body_size),
                
                # الحشو الداخلي
                ('TOPPADDING', (0, 0), (-1, -1), vertical_padding),
                ('BOTTOMPADDING', (0, 0), (-1, -1), vertical_padding),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                
                # تباعد الأسطر
                ('LEADING', (0, 0), (-1, -1), body_size * line_spacing),
            ]

            # إضافة ألوان الصفوف بناءً على الحالة
            for i, rec in enumerate(today_records):
                row_idx = i + 1  # +1 لأن الصف 0 هو الرأس
                is_deleted = rec.get("deleted", False)
                is_edited = rec.get("edited", False)
                needs_recon = rec.get("needs_reconciliation", False)
                is_reconciled = rec.get("reconciled", False)

                if is_deleted:
                    style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), deleted_bg))
                    style_commands.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), deleted_text))
                elif is_edited:
                    style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), edited_bg))
                    style_commands.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), edited_text))
                elif needs_recon and not is_reconciled:
                    style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), pending_bg))
                    style_commands.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), pending_text))
                elif needs_recon and is_reconciled:
                    style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), reconciled_bg))
                    style_commands.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), reconciled_text))

            t.setStyle(TableStyle(style_commands))

            # حساب المساحة المتاحة ورسم الجدول
            available_height = y_table_start - 50
            t.wrapOn(c, width - margins["left"] - margins["right"], available_height)
            
            # التحقق مما إذا كان الجدول يحتاج لصفحات متعددة
            table_height = t._height
            current_y = y_table_start
            
            # رسم الجدول
            t.drawOn(c, margins["left"], current_y - table_height)

            c.save()

            if sys.platform == "win32":
                os.startfile(report_path)
            elif sys.platform == "darwin":
                subprocess.call(["open", report_path])
            else:
                subprocess.call(["xdg-open", report_path])

            messagebox.showinfo("نجاح", f"تم إنشاء تقرير اليوم\nالمسار: {report_path}")

        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء إنشاء التقرير: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = SarfApp(root)
    root.mainloop()