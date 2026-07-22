from __future__ import annotations

from datetime import date
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


OUTPUT = Path(__file__).resolve().parents[1] / "Totem_Project_專案成果暨技術文件範本.docx"


def run(text: str, *, bold: bool = False, size: int = 22, color: str | None = None) -> str:
    props = [f'<w:sz w:val="{size}"/>', f'<w:szCs w:val="{size}"/>']
    if bold:
        props.append("<w:b/>")
    if color:
        props.append(f'<w:color w:val="{color}"/>')
    props.append('<w:rFonts w:ascii="Aptos" w:hAnsi="Aptos" w:eastAsia="Microsoft JhengHei"/>')
    return f'<w:r><w:rPr>{"".join(props)}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def paragraph(text: str = "", *, style: str | None = None, bold: bool = False,
              align: str | None = None, before: int = 0, after: int = 120,
              keep: bool = False, shade: str | None = None) -> str:
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if align:
        ppr.append(f'<w:jc w:val="{align}"/>')
    if keep:
        ppr.append("<w:keepNext/>")
    ppr.append(f'<w:spacing w:before="{before}" w:after="{after}" w:line="360" w:lineRule="auto"/>')
    if shade:
        ppr.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>')
    return f'<w:p><w:pPr>{"".join(ppr)}</w:pPr>{run(text, bold=bold)}</w:p>'


def bullet(text: str, level: int = 0) -> str:
    return (
        '<w:p><w:pPr><w:pStyle w:val="ListParagraph"/>'
        f'<w:numPr><w:ilvl w:val="{level}"/><w:numId w:val="1"/></w:numPr>'
        '<w:spacing w:after="80" w:line="320" w:lineRule="auto"/></w:pPr>'
        f'{run(text)}</w:p>'
    )


def note(text: str) -> str:
    return paragraph("填寫提示｜" + text, bold=True, shade="EAF3F2", before=80, after=120)


def placeholder(text: str, lines: int = 2) -> str:
    body = paragraph(f"【請填寫】{text}", shade="F3F4F6")
    for _ in range(lines - 1):
        body += paragraph(" ", shade="F3F4F6")
    return body


def page_break() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def cell(text: str, *, header: bool = False, width: int = 2400) -> str:
    fill = '<w:shd w:val="clear" w:fill="DCEAE8"/>' if header else ""
    return (
        f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{fill}</w:tcPr>'
        f'{paragraph(text, bold=header, after=40)}</w:tc>'
    )


def table(rows: list[list[str]], header: bool = True, widths: list[int] | None = None) -> str:
    xml = ['<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/>'
           '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" '
           'w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>']
    for i, row in enumerate(rows):
        xml.append("<w:tr>")
        for j, value in enumerate(row):
            width = widths[j] if widths and j < len(widths) else 2400
            xml.append(cell(value, header=header and i == 0, width=width))
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    return "".join(xml) + paragraph("")


def heading(text: str, level: int = 1) -> str:
    return paragraph(text, style=f"Heading{level}", keep=True, before=220, after=100)


def section(title: str, intro: str, items: list[str], prompts: list[tuple[str, int]] | None = None) -> str:
    xml = heading(title, 1) + note(intro)
    for item in items:
        xml += bullet(item)
    if prompts:
        for label, lines in prompts:
            xml += placeholder(label, lines)
    return xml


def document_body() -> str:
    parts: list[str] = []
    parts += [
        paragraph("TOTEM PROJECT", bold=True, align="center", before=1200, after=120),
        '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:after="240"/></w:pPr>'
        + run("專案成果暨技術文件", bold=True, size=44, color="185B56") + '</w:p>',
        paragraph("具多輪狀態管理的自然語言 AI 圖騰設計系統", align="center", after=700),
        table([
            ["文件資訊", "內容"],
            ["作者", "【請填寫姓名】"],
            ["部門／單位", "【請填寫】"],
            ["專案期間", "【YYYY/MM－YYYY/MM】"],
            ["文件版本", "v1.0"],
            ["提交日期", str(date.today())],
            ["文件用途", "主管成果交付／作品集／升學申請素材"],
        ], widths=[2600, 6000]),
        paragraph("文件機密等級：【公開／內部使用／機密】", align="center", before=500),
        page_break(),
        heading("文件修訂紀錄", 1),
        table([
            ["版本", "日期", "修訂者", "修訂內容"],
            ["v0.1", "【日期】", "【姓名】", "建立初稿"],
            ["v1.0", "【日期】", "【姓名】", "正式提交"],
        ], widths=[1200, 1800, 1800, 4200]),
        heading("閱讀指南", 1),
        bullet("主管／專案接手者：優先閱讀第 1、4、5、9、11、12 章。"),
        bullet("技術審查者：優先閱讀第 5～8、10 章及附錄。"),
        bullet("作品集／升學申請：可擷取第 1～4、7、11、12 章。"),
        note("灰底【請填寫】區塊為待補內容；完成後可刪除所有填寫提示。圖片請補上編號、標題及一句解讀。"),
        heading("目錄", 1),
        '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        + run("請在 Microsoft Word 中按 Ctrl+A，再按 F9 更新目錄與頁碼。", color="666666")
        + '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>',
        page_break(),
    ]

    parts.append(section(
        "1. 專案摘要",
        "控制在一頁內，讓讀者快速理解問題、解法、核心差異與你的貢獻。",
        ["專案名稱與一句話定位", "開發背景與期間", "目標使用者與核心問題", "四項核心能力", "目前完成狀態", "個人角色與負責範圍", "可量化成果"],
        [("一句話專案定位", 2), ("150～250 字摘要", 5), ("個人負責範圍（請明確區分個人與團隊）", 3), ("成果數據摘要；尚未測量者請標示待驗證", 3)],
    ))
    parts.append(heading("1.1 核心亮點", 2))
    parts.append(table([
        ["核心能力", "重點說明", "成果證據"],
        ["同構圖多配色", "同一圖騰輸出四種配色，構圖、輪廓與元素位置一致。", "【截圖／測試結果】"],
        ["語意式配色編輯", "理解保留、替換、隨機及色彩風格要求，構圖不變。", "【案例／準確率】"],
        ["生成式設計修改", "新增、移除或替換元素後重新進入 Image Model 生圖。", "【前後版本比較】"],
        ["多輪迭代", "累積每一輪保留、移除、排除與配色條件。", "【完整對話案例】"],
    ], widths=[1800, 4700, 2200]))
    parts.append(page_break())

    parts.append(section(
        "2. 專案背景與問題定義",
        "先描述原有流程與痛點，再說明為何需要結合語言模型、圖像模型與傳統圖像處理。",
        ["原有圖騰設計流程", "傳統流程與一般 AI 生圖的限制", "使用者痛點", "專案目標與成功條件", "專案範圍", "本階段不處理項目"],
        [("背景與實際情境", 4), ("問題陳述：誰在什麼情境遇到什麼困難", 4), ("專案目標與驗收標準", 4), ("範圍與非範圍", 3)],
    ))
    parts.append(page_break())

    parts.append(section(
        "3. 使用者需求與使用情境",
        "使用具體角色、任務與操作情境，避免只列技術功能。",
        ["目標使用者", "主要任務", "功能需求", "非功能需求", "User Story", "完整使用流程"],
        [("目標使用者及其需求", 3)],
    ))
    parts.append(heading("3.1 User Story 範本", 2))
    parts.append(table([
        ["角色", "我希望……", "以便……", "驗收條件"],
        ["非專業設計使用者", "選擇元素並以自然語言描述需求", "不需撰寫複雜 Prompt", "能成功產生符合元素需求的圖騰"],
        ["商品企劃", "比較相同構圖的不同配色", "專注評估色彩方案", "四張圖片只有配色不同"],
        ["【角色】", "【需求】", "【價值】", "【可測試條件】"],
    ], widths=[1800, 2900, 2500, 2500]))
    parts.append(page_break())

    parts.append(heading("4. 核心功能說明", 1))
    parts.append(note("每項功能皆建議依『使用者輸入 → 系統處理 → 輸出 → 使用價值 → 成果證據』描述。"))
    core_sections = [
        ("4.1 初始圖騰生成", ["元素選擇", "自由文字補充需求", "結構化設計條件", "Prompt 編譯", "Image Model 生成", "生成紀錄保存"]),
        ("4.2 同構圖多配色輸出", ["建立基礎圖騰", "輸出四種配色", "構圖、元素位置及輪廓一致", "色票資訊", "配色比較"]),
        ("4.3 自然語言配色修改", ["自由文字輸入", "保留／替換／隨機／風格意圖辨識", "結構化配色規則", "顏色映射", "不重新生成、構圖不變"]),
        ("4.4 元素與構圖重新生成", ["元素新增、移除及替換", "元素與配色複合修改", "Design Spec 更新", "Prompt 重編譯", "Image Model 重新生成"]),
        ("4.5 多輪迭代設計", ["上一輪狀態繼承", "保留與排除條件", "本輪要求合併", "兩種修改模式切換", "版本關聯與追溯"]),
        ("4.6 延伸功能", ["商品 Mockup", "Repeat Pattern", "十字繡圖表", "收藏與 Collection", "圖片及資產管理"]),
    ]
    for title, bullets in core_sections:
        parts.append(heading(title, 2))
        for item in bullets:
            parts.append(bullet(item))
        parts.append(placeholder("功能說明及代表性使用案例", 3))
        parts.append(placeholder("插入操作畫面／輸入與輸出比較圖", 2))
    parts.append(page_break())

    parts.append(heading("5. 系統流程與模式判斷", 1))
    parts.append(note("清楚區分『構圖不變的精準換色』與『重新呼叫 Image Model 的生成式修改』。"))
    parts.append(heading("5.1 整體流程", 2))
    parts.append(placeholder("插入整體流程圖：初始生成 → 多配色 → 語意分類 → 配色修改／重新生成 → 狀態更新", 5))
    parts.append(heading("5.2 修改模式比較", 2))
    parts.append(table([
        ["比較項目", "語意式配色編輯", "生成式設計修改"],
        ["顏色", "可修改", "可修改"],
        ["元素", "不修改", "可新增、移除或替換"],
        ["構圖", "保持相同", "可重新生成"],
        ["Image Model", "不重新呼叫", "重新呼叫"],
        ["上一輪狀態", "延續", "延續"],
    ], widths=[2600, 3200, 3200]))
    parts.append(heading("5.3 模式判斷規則", 2))
    parts.append(placeholder("描述系統如何從自然語言判斷修改類型、衝突條件及例外處理", 5))
    parts.append(page_break())

    parts.append(section(
        "6. 系統架構",
        "說明前端、後端、AI、圖像處理、資料儲存與部署元件之間的責任邊界。",
        ["整體架構圖", "React／TypeScript／Vite 前端", "FastAPI 後端", "OpenAI 文字與圖像模型", "Pillow 圖像處理", "Catalog／資料庫／圖片儲存", "AWS EC2、Nginx 與 systemd"],
        [("插入系統架構圖", 5), ("各元件責任及選用原因", 5), ("關鍵技術選擇與替代方案比較", 4)],
    ))
    parts.append(page_break())

    parts.append(section(
        "7. 技術設計與關鍵實作",
        "此章呈現技術深度，採用『問題 → 設計 → 實作 → 驗證 → 取捨』結構。",
        ["語意理解與結構化輸出", "Prompt Compiler", "Revision Resolver", "顏色擷取、映射與保留", "多輪狀態管理", "錯誤與衝突處理"],
        [],
    ))
    for title in ["7.1 語意理解設計", "7.2 Prompt Compiler", "7.3 Revision Resolver", "7.4 顏色處理", "7.5 多輪狀態管理"]:
        parts.append(heading(title, 2))
        parts.append(placeholder("欲解決的技術問題", 2))
        parts.append(placeholder("設計與實作方式", 4))
        parts.append(placeholder("選擇此方案的理由、限制與驗證結果", 3))
    parts.append(page_break())

    parts.append(heading("8. 資料與 API 設計", 1))
    parts.append(note("欄位及 Endpoint 以實際程式為準；應保存原始需求、編譯後 Prompt、設計狀態與版本關係。"))
    parts.append(heading("8.1 資料模型", 2))
    parts.append(table([
        ["資料物件", "用途", "重要欄位"],
        ["Image Record", "保存一次生成及其相關資產", "id、files、parent_id、created_at"],
        ["Generation", "保存生成條件", "user_prompt、elements、compiled_prompt"],
        ["Palette", "保存顏色資訊", "colors、rgb、palette_name"],
        ["Design Spec", "保存可迭代設計狀態", "added、removed、excluded、palette_instruction"],
        ["【其他】", "【用途】", "【欄位】"],
    ], widths=[1900, 3000, 4100]))
    parts.append(heading("8.2 API 清單", 2))
    parts.append(table([
        ["Method", "Endpoint", "功能", "狀態"],
        ["POST", "/api/v1/images/generate", "初始圖騰生成", "【完成／進行中】"],
        ["POST", "/api/v1/images/{id}/regenerate", "生成式修改", "【完成／進行中】"],
        ["【Method】", "【Endpoint】", "【功能】", "【狀態】"],
    ], widths=[1200, 3500, 2800, 1700]))
    parts.append(placeholder("補充 Request／Response 範例、錯誤碼與驗證規則", 5))
    parts.append(page_break())

    parts.append(section(
        "9. 使用介面與操作說明",
        "每項操作放置畫面截圖、步驟、輸入範例、預期輸出與注意事項。",
        ["首頁與元素選擇", "文字需求輸入", "初始生成", "四種配色比較", "自然語言換色", "元素重新生成", "版本瀏覽", "商品預覽", "收藏與 Collection", "錯誤處理"],
        [("完整操作流程與畫面截圖", 8), ("常見操作問題與處理方式", 4)],
    ))
    parts.append(page_break())

    parts.append(heading("10. 測試與品質驗證", 1))
    parts.append(note("AI 功能除了程式測試，也需定義語意遵循率、構圖一致率及多輪狀態一致率。"))
    parts.append(heading("10.1 測試策略", 2))
    for item in ["單元測試", "API／整合測試", "前端 Build 與靜態檢查", "圖像結果比較", "AI 指令遵循評估", "人工使用情境測試"]:
        parts.append(bullet(item))
    parts.append(heading("10.2 測試案例紀錄", 2))
    parts.append(table([
        ["編號", "輸入／情境", "預期結果", "實際結果", "狀態"],
        ["TC-01", "紅色換成綠色", "僅指定顏色改變，構圖不變", "【填寫】", "【通過／失敗】"],
        ["TC-02", "保留紅色，其餘隨機配色", "紅色不變，其餘顏色更新", "【填寫】", "【通過／失敗】"],
        ["TC-03", "將太陽換成月亮", "元素更新並重新生成構圖", "【填寫】", "【通過／失敗】"],
        ["TC-04", "連續四輪修改", "正確延續、移除及排除條件", "【填寫】", "【通過／失敗】"],
    ], widths=[1000, 2500, 3000, 2000, 1500]))
    parts.append(heading("10.3 評估指標", 2))
    parts.append(table([
        ["指標", "定義", "測量方式", "目前結果"],
        ["構圖一致率", "配色修改前後輪廓及元素位置一致", "影像差異／人工驗證", "【待測量】"],
        ["配色指令遵循率", "正確完成保留與替換要求", "通過案例數／總案例數", "【待測量】"],
        ["元素指令遵循率", "正確新增、移除或替換元素", "人工標註", "【待測量】"],
        ["多輪狀態一致率", "正確繼承歷史限制", "多輪案例測試", "【待測量】"],
        ["平均處理時間", "從提交到顯示結果", "系統紀錄", "【待測量】"],
    ], widths=[1900, 3100, 2600, 1800]))
    parts.append(page_break())

    parts.append(section(
        "11. 專案成果、效益與限制",
        "成果需附證據；尚未實測的效益不可寫成既成事實。",
        ["已完成功能", "技術成果", "使用者價值", "量化成果", "代表性案例", "目前限制", "風險與因應方式"],
        [("已完成成果與證據", 5), ("量化成果；未量測請寫待驗證", 4), ("目前限制與原因", 4), ("風險、影響及因應方式", 4)],
    ))
    parts.append(page_break())

    parts.append(section(
        "12. 未來規劃與個人貢獻",
        "用短、中、長期規劃呈現可行性，並明確區分個人貢獻與團隊成果。",
        ["產品功能規劃", "工程改善", "部署與維運規劃", "個人負責模組", "關鍵技術決策", "跨角色合作", "學習與反思"],
        [("短期規劃（1～3 個月）", 3), ("中長期規劃", 3), ("我的具體貢獻", 5), ("最具挑戰的問題及解法", 4), ("如果重新開發，我會如何改善", 3), ("本專案帶來的學習與能力成長", 4)],
    ))
    parts.append(page_break())

    parts.append(heading("附錄 A：API 規格", 1))
    parts.append(placeholder("完整 Endpoint、Request、Response、錯誤代碼與呼叫範例", 8))
    parts.append(heading("附錄 B：資料格式", 1))
    parts.append(placeholder("Image Record、Palette、Design Spec、Revision History 與 Collection 範例", 8))
    parts.append(heading("附錄 C：安裝與執行", 1))
    parts.append(placeholder("環境需求、環境變數、前後端啟動、測試指令與常見錯誤", 8))
    parts.append(heading("附錄 D：部署與維護", 1))
    parts.append(placeholder("EC2、Nginx、systemd、資料備份、Log、更新流程與故障排除", 8))
    parts.append(heading("附錄 E：作品集／履歷素材", 1))
    parts.append(placeholder("150 字作品摘要", 4))
    parts.append(placeholder("3～5 條履歷 bullet；每條使用『行動＋技術＋成果』", 5))
    parts.append(placeholder("代表性圖片清單及可公開範圍", 4))

    parts.append(
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1276" '
        'w:header="720" w:footer="720" w:gutter="0"/>'
        '<w:headerReference w:type="default" r:id="rIdHeader1"/>'
        '<w:footerReference w:type="default" r:id="rIdFooter1"/>'
        '</w:sectPr>'
    )
    return "".join(parts)


CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''

ROOT_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''

DOC_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rIdNumbering" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
<Relationship Id="rIdHeader1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
<Relationship Id="rIdFooter1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
</Relationships>'''

STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos" w:eastAsia="Microsoft JhengHei"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="120" w:line="360" w:lineRule="auto"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:pageBreakBefore/><w:outlineLvl w:val="0"/><w:spacing w:before="240" w:after="160"/></w:pPr><w:rPr><w:rFonts w:eastAsia="Microsoft JhengHei"/><w:b/><w:color w:val="185B56"/><w:sz w:val="34"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:outlineLvl w:val="1"/><w:spacing w:before="220" w:after="100"/></w:pPr><w:rPr><w:b/><w:color w:val="24756F"/><w:sz w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="720"/></w:pPr></w:style>
<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:color="B8C4C2"/><w:left w:val="single" w:sz="4" w:color="B8C4C2"/><w:bottom w:val="single" w:sz="4" w:color="B8C4C2"/><w:right w:val="single" w:sz="4" w:color="B8C4C2"/><w:insideH w:val="single" w:sz="4" w:color="B8C4C2"/><w:insideV w:val="single" w:sz="4" w:color="B8C4C2"/></w:tblBorders><w:tblCellMar><w:top w:w="100" w:type="dxa"/><w:left w:w="100" w:type="dxa"/><w:bottom w:w="100" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
</w:styles>'''

NUMBERING = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/>
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/><w:pPr><w:tabs><w:tab w:val="num" w:pos="720"/></w:tabs><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl>
<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="–"/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="1440" w:hanging="360"/></w:pPr></w:lvl>
</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
</w:numbering>'''


def create_docx() -> None:
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>'
                + document_body() + '</w:body></w:document>')
    settings = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:updateFields w:val="true"/><w:defaultTabStop w:val="720"/></w:settings>')
    header = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              + paragraph("TOTEM PROJECT｜專案成果暨技術文件", after=0) + '</w:hdr>')
    footer = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
              '<w:r><w:t>第 </w:t></w:r><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
              '<w:r><w:instrText> PAGE </w:instrText></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>'
              '<w:r><w:t> 頁</w:t></w:r></w:p></w:ftr>')
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>Totem Project 專案成果暨技術文件範本</dc:title><dc:creator>Totem Project</dc:creator><dc:subject>AI 圖騰設計系統技術文件</dc:subject><dcterms:created xsi:type="dcterms:W3CDTF">{date.today()}T00:00:00Z</dcterms:created></cp:coreProperties>'''
    app = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Microsoft Office Word</Application><Company>Totem Project</Company></Properties>'''

    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", ROOT_RELS)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/_rels/document.xml.rels", DOC_RELS)
        archive.writestr("word/styles.xml", STYLES)
        archive.writestr("word/numbering.xml", NUMBERING)
        archive.writestr("word/settings.xml", settings)
        archive.writestr("word/header1.xml", header)
        archive.writestr("word/footer1.xml", footer)
        archive.writestr("docProps/core.xml", core)
        archive.writestr("docProps/app.xml", app)
    print(OUTPUT)


if __name__ == "__main__":
    create_docx()
