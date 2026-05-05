# -*- coding: utf-8 -*-
"""
fix_ai_chat_continuous.py

Исправляет ИИ-чат:
1) сообщение пользователя сразу видно в чате;
2) после первого ответа можно писать второй вопрос;
3) кнопка и поле ввода всегда возвращаются в рабочее состояние;
4) история чата не стирается после каждого ответа;
5) можно спрашивать общие вопросы по недвижимости даже без выбранного объекта.

Запуск:
python fix_ai_chat_continuous.py
"""

from pathlib import Path
import re
import shutil
import py_compile

MAIN_PATH = Path("main.py")
if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py не найден. Запусти из папки проекта.")

backup = Path("main.py.backup_ai_chat_continuous")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

BUILD_AI_TAB = "    def _build_ai_tab(self) -> QWidget:\n        \"\"\"\n        Нормальный чат ИИ-ассистента:\n        - сообщения пользователя видны в чате;\n        - после ответа можно писать следующий вопрос;\n        - ИИ работает даже без выбранного объекта, но лучше с выбранным объектом.\n        \"\"\"\n        widget = QWidget()\n        widget.setStyleSheet(\"background:#ffffff;color:#111827;\")\n\n        layout = QVBoxLayout(widget)\n        layout.setContentsMargins(8, 8, 8, 8)\n        layout.setSpacing(7)\n\n        title = QLabel(\"🤖 ИИ-чат по недвижимости Алматы\")\n        title.setObjectName(\"sectionLabel\")\n        title.setStyleSheet(\"color:#1a237e;font-size:14px;font-weight:900;background:#ffffff;\")\n        layout.addWidget(title)\n\n        self.ai_context_label = QLabel(\"Можно писать вопрос. Для точного анализа выберите объект на карте и нажмите ✅ Выбрать.\")\n        self.ai_context_label.setWordWrap(True)\n        self.ai_context_label.setMaximumHeight(76)\n        self.ai_context_label.setStyleSheet(\n            \"background:#eef2ff;color:#111827;border:1px solid #c7d2fe;\"\n            \"border-radius:10px;padding:8px;font-size:12px;font-weight:600;\"\n        )\n        layout.addWidget(self.ai_context_label)\n\n        # История сообщений\n        self.ai_history = []\n        self.ai_busy = False\n\n        quick_grid = QVBoxLayout()\n        quick_grid.setSpacing(5)\n\n        quick_questions = [\n            [\"Привет\", \"Что ты умеешь?\", \"Что влияет на цену?\"],\n            [\"Почему такая цена?\", \"Дорого для района?\", \"Какие риски?\"],\n            [\"Можно торговаться?\", \"Подходит для жизни?\", \"Полный анализ объекта\"],\n        ]\n\n        for row_questions in quick_questions:\n            row = QHBoxLayout()\n            row.setSpacing(5)\n            for q in row_questions:\n                btn = QPushButton(q)\n                btn.setMinimumHeight(30)\n                btn.setStyleSheet(\n                    \"QPushButton { background:#e8eaf6;color:#1a237e;border:1px solid #c7d2fe;\"\n                    \"border-radius:8px;font-size:11px;font-weight:700;padding:4px 6px; }\"\n                    \"QPushButton:hover { background:#dbeafe; }\"\n                )\n                btn.clicked.connect(lambda checked=False, text=q: self._quick_question(text))\n                row.addWidget(btn)\n            quick_grid.addLayout(row)\n\n        layout.addLayout(quick_grid)\n\n        self.ai_response = QTextEdit()\n        self.ai_response.setReadOnly(True)\n        self.ai_response.setAcceptRichText(True)\n        self.ai_response.setLineWrapMode(QTextEdit.WidgetWidth)\n        self.ai_response.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)\n        self.ai_response.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)\n        self.ai_response.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)\n        self.ai_response.setStyleSheet(\n            \"QTextEdit { background:#ffffff; color:#111827; border:1px solid #d8dee9; \"\n            \"border-radius:10px; padding:10px; font-size:12px; line-height:1.6; }\"\n            \"QScrollBar:vertical { background:#f1f5f9; width:14px; border-radius:7px; }\"\n            \"QScrollBar::handle:vertical { background:#94a3b8; border-radius:7px; min-height:35px; }\"\n        )\n        layout.addWidget(self.ai_response, stretch=1)\n\n        input_row = QHBoxLayout()\n        input_row.setSpacing(6)\n\n        self.ai_input = QLineEdit()\n        self.ai_input.setPlaceholderText(\"Напиши вопрос в чат: цена, район, риски, торг, инфраструктура...\")\n        self.ai_input.setMinimumHeight(38)\n        self.ai_input.setEnabled(True)\n        self.ai_input.returnPressed.connect(self._ask_ai)\n        input_row.addWidget(self.ai_input, stretch=1)\n\n        self.ai_ask_btn = QPushButton(\"Отправить\")\n        self.ai_ask_btn.setObjectName(\"applyFilterBtn\")\n        self.ai_ask_btn.setMinimumHeight(38)\n        self.ai_ask_btn.setMinimumWidth(110)\n        self.ai_ask_btn.clicked.connect(self._ask_ai)\n        input_row.addWidget(self.ai_ask_btn)\n\n        layout.addLayout(input_row)\n\n        self._append_ai_message(\n            \"assistant\",\n            \"Привет! Я ИИ-ассистент по недвижимости Алматы. Можешь писать мне обычным сообщением. \"\n            \"Для точного анализа выбери квартиру на карте и нажми зелёную кнопку **✅ Выбрать**.\"\n        )\n\n        return widget\n"
APPEND_METHOD = "    def _append_ai_message(self, role: str, text: str):\n        \"\"\"Добавляет сообщение в историю ИИ-чата и перерисовывает чат.\"\"\"\n        if not hasattr(self, \"ai_history\"):\n            self.ai_history = []\n\n        self.ai_history.append({\n            \"role\": role,\n            \"text\": str(text or \"\")\n        })\n\n        # Чтобы чат не разрастался бесконечно\n        if len(self.ai_history) > 40:\n            self.ai_history = self.ai_history[-40:]\n\n        self._render_ai_history()\n"
RENDER_METHOD = "    def _render_ai_history(self):\n        \"\"\"Рисует историю сообщений как чат.\"\"\"\n        import html as _html\n        import re\n\n        def md_inline(s: str) -> str:\n            s = _html.escape(str(s))\n            s = re.sub(r\"\\*\\*(.*?)\\*\\*\", r\"<b>\\1</b>\", s)\n            s = re.sub(r\"`([^`]+)`\", r\"<code style='background:#f1f5f9;padding:1px 4px;border-radius:4px'>\\1</code>\", s)\n            return s\n\n        def md_block(text: str) -> str:\n            parts = []\n            in_list = False\n\n            def close_list():\n                nonlocal in_list\n                if in_list:\n                    parts.append(\"</ul>\")\n                    in_list = False\n\n            for raw in str(text or \"\").splitlines():\n                line = raw.rstrip()\n\n                if not line.strip():\n                    close_list()\n                    parts.append(\"<div style='height:5px'></div>\")\n                    continue\n\n                if line.startswith(\"## \"):\n                    close_list()\n                    parts.append(\n                        f\"<h3 style='margin:10px 0 5px;color:#1a237e;font-size:15px'>{md_inline(line[3:].strip())}</h3>\"\n                    )\n                    continue\n\n                if line.startswith(\"# \"):\n                    close_list()\n                    parts.append(\n                        f\"<h2 style='margin:10px 0 6px;color:#1a237e;font-size:16px'>{md_inline(line[2:].strip())}</h2>\"\n                    )\n                    continue\n\n                if line.startswith(\"- \") or line.startswith(\"• \"):\n                    if not in_list:\n                        parts.append(\"<ul style='margin:4px 0 8px 18px;padding:0'>\")\n                        in_list = True\n                    parts.append(f\"<li style='margin:3px 0'>{md_inline(line[2:].strip())}</li>\")\n                    continue\n\n                close_list()\n                parts.append(f\"<p style='margin:4px 0'>{md_inline(line.strip())}</p>\")\n\n            close_list()\n            return \"\".join(parts)\n\n        html = (\n            \"<div style='font-family:Segoe UI,Arial,sans-serif;color:#111827;\"\n            \"background:#ffffff;font-size:12px;line-height:1.55;'>\"\n        )\n\n        for msg in getattr(self, \"ai_history\", []):\n            role = msg.get(\"role\")\n            text = msg.get(\"text\", \"\")\n\n            if role == \"user\":\n                html += (\n                    \"<div style='margin:8px 0;text-align:right;'>\"\n                    \"<div style='display:inline-block;max-width:82%;background:#2563eb;color:white;\"\n                    \"padding:9px 12px;border-radius:14px 14px 4px 14px;text-align:left;font-weight:600;'>\"\n                    f\"{md_inline(text)}\"\n                    \"</div></div>\"\n                )\n            else:\n                html += (\n                    \"<div style='margin:8px 0;text-align:left;'>\"\n                    \"<div style='display:inline-block;max-width:92%;background:#f8fafc;color:#111827;\"\n                    \"border:1px solid #e2e8f0;padding:10px 12px;border-radius:14px 14px 14px 4px;text-align:left;'>\"\n                    f\"{md_block(text)}\"\n                    \"</div></div>\"\n                )\n\n        html += \"</div>\"\n\n        if hasattr(self, \"ai_response\"):\n            self.ai_response.setHtml(html)\n            try:\n                self.ai_response.verticalScrollBar().setValue(self.ai_response.verticalScrollBar().maximum())\n            except Exception:\n                pass\n"
ASK_METHOD = "    def _ask_ai(self):\n        \"\"\"\n        Отправка сообщения в ИИ-чат.\n        Исправлено:\n        - сообщение пользователя сразу видно в чате;\n        - поле ввода очищается;\n        - после ответа можно писать второй/третий вопрос;\n        - без выбранного объекта ИИ всё равно отвечает на общие вопросы по недвижимости.\n        \"\"\"\n        if not hasattr(self, \"ai_input\"):\n            return\n\n        question = self.ai_input.text().strip()\n        if not question:\n            return\n\n        if getattr(self, \"ai_busy\", False):\n            try:\n                self.status_bar.showMessage(\"Подождите, ИИ ещё отвечает на предыдущий вопрос.\", 4000)\n            except Exception:\n                pass\n            return\n\n        self.ai_input.clear()\n        self._append_ai_message(\"user\", question)\n\n        # Контекст: выбранный объект, либо объект, кликнутый на карте, но ещё не подтверждённый\n        prop_context = getattr(self, \"selected_prop\", None)\n        if prop_context is None:\n            prop_context = getattr(self, \"pending_prop\", None)\n        if prop_context is None:\n            prop_context = {}\n\n        try:\n            if prop_context and hasattr(self, \"_ensure_selected_microdistrict\"):\n                # Если объект уже выбран, можно уточнить микрорайон\n                self._ensure_selected_microdistrict()\n        except Exception:\n            pass\n\n        # Microdistrict stats считаем быстро только в момент вопроса\n        micro_stats = {}\n        try:\n            if self.df is not None and \"microdistrict\" in self.df.columns and \"price_per_m2\" in self.df.columns:\n                grouped = self.df.groupby(\"microdistrict\")[\"price_per_m2\"]\n                for name, group in grouped:\n                    vals = group.dropna()\n                    if len(vals) > 0 and str(name).strip() and str(name).strip() != \"Не определён\":\n                        micro_stats[str(name)] = {\n                            \"avg\": float(vals.mean()),\n                            \"median\": float(vals.median()),\n                            \"count\": int(len(vals)),\n                        }\n        except Exception:\n            micro_stats = {}\n\n        self.ai_busy = True\n        self.ai_ask_btn.setEnabled(False)\n        self.ai_ask_btn.setText(\"Думаю...\")\n        self.ai_input.setEnabled(True)\n        self.ai_input.setPlaceholderText(\"ИИ отвечает... скоро можно будет задать следующий вопрос\")\n\n        self._append_ai_message(\"assistant\", \"⏳ Думаю...\")\n\n        try:\n            self.ai_thread = AIThread(\n                prop_context,\n                question,\n                self.district_stats,\n                micro_stats,\n                self.nearby_places,\n            )\n            self.ai_thread.resultReady.connect(self._on_ai_result)\n            self.ai_thread.finished.connect(self._on_ai_finished)\n            self.ai_thread.start()\n        except Exception as e:\n            # Если поток не стартовал, сразу возвращаем управление\n            if self.ai_history and self.ai_history[-1][\"text\"] == \"⏳ Думаю...\":\n                self.ai_history.pop()\n            self._append_ai_message(\"assistant\", f\"Ошибка запуска ассистента: {e}\")\n            self._on_ai_finished()\n"
ON_RESULT = "    def _on_ai_result(self, answer: str):\n        \"\"\"Получили ответ ИИ: заменяем временное 'Думаю...' на настоящий ответ.\"\"\"\n        try:\n            if hasattr(self, \"ai_history\") and self.ai_history:\n                if self.ai_history[-1].get(\"role\") == \"assistant\" and \"Думаю\" in self.ai_history[-1].get(\"text\", \"\"):\n                    self.ai_history.pop()\n\n            self._append_ai_message(\"assistant\", answer)\n        except Exception:\n            try:\n                self.ai_response.setHtml(self._markdown_to_html(answer))\n            except Exception:\n                pass\n"
ON_FINISHED = "    def _on_ai_finished(self):\n        \"\"\"Всегда возвращает поле ввода и кнопку после завершения ответа.\"\"\"\n        self.ai_busy = False\n\n        try:\n            self.ai_ask_btn.setEnabled(True)\n            self.ai_ask_btn.setText(\"Отправить\")\n        except Exception:\n            pass\n\n        try:\n            self.ai_input.setEnabled(True)\n            self.ai_input.setPlaceholderText(\"Напиши следующий вопрос...\")\n            self.ai_input.setFocus()\n        except Exception:\n            pass\n\n        try:\n            self.ai_thread.deleteLater()\n        except Exception:\n            pass\n"
QUICK = "    def _quick_question(self, question: str):\n        \"\"\"Быстрый вопрос теперь тоже отправляется как обычное сообщение в чат.\"\"\"\n        if hasattr(self, \"ai_input\"):\n            self.ai_input.setText(question)\n        try:\n            self.tabs.setCurrentIndex(2)\n        except Exception:\n            pass\n        self._ask_ai()\n"

def method_bounds(source: str, method_name: str):
    matches = list(re.finditer(rf"(?m)^    def {re.escape(method_name)}\s*\(", source))
    if not matches:
        return None
    m = matches[0]
    next_m = re.search(r"(?m)^    def \w+\s*\(", source[m.end():])
    end = m.end() + next_m.start() if next_m else len(source)
    return m.start(), end

def replace_or_insert(source: str, method_name: str, new_method: str, before_method: str | None = None) -> str:
    bounds = method_bounds(source, method_name)
    if bounds:
        start, end = bounds
        print("Replaced:", method_name)
        return source[:start] + new_method.rstrip() + "\n" + source[end:]

    if before_method:
        marker = "\n    def " + before_method
        if marker in source:
            print("Inserted:", method_name, "before", before_method)
            return source.replace(marker, "\n" + new_method.rstrip() + "\n" + marker, 1)

    marker = "\n    def _ask_ai"
    if marker in source:
        print("Inserted:", method_name, "before _ask_ai")
        return source.replace(marker, "\n" + new_method.rstrip() + "\n" + marker, 1)

    raise RuntimeError(f"Не найден метод {method_name} и место для вставки.")

text = replace_or_insert(text, "_build_ai_tab", BUILD_AI_TAB, "_quick_question")
text = replace_or_insert(text, "_append_ai_message", APPEND_METHOD, "_render_ai_history")
text = replace_or_insert(text, "_render_ai_history", RENDER_METHOD, "_quick_question")
text = replace_or_insert(text, "_quick_question", QUICK, "_ask_ai")
text = replace_or_insert(text, "_ask_ai", ASK_METHOD, "_on_ai_result")
text = replace_or_insert(text, "_on_ai_result", ON_RESULT, "_on_ai_finished")
text = replace_or_insert(text, "_on_ai_finished", ON_FINISHED, "_markdown_to_html")

MAIN_PATH.write_text(text, encoding="utf-8")
py_compile.compile(str(MAIN_PATH), doraise=True)

print("DONE: AI continuous chat fixed.")
print("Run: python main.py")
