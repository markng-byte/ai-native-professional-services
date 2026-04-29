import zipfile
import xml.etree.ElementTree as ET
import sys

def read_excel(file_path):
    out = open("excel_content.md", "w", encoding="utf-8")
    with zipfile.ZipFile(file_path, 'r') as z:
        shared_strings = []
        try:
            with z.open('xl/sharedStrings.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                namespace = {'ns': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
                for si in root.findall('.//ns:t', namespace) if namespace else root.findall('.//t'):
                    shared_strings.append(si.text if si.text else "")
        except KeyError:
            pass

        with z.open('xl/workbook.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            namespace = {'ns': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
            sheets = []
            for sheet in root.findall('.//ns:sheet', namespace) if namespace else root.findall('.//sheet'):
                sheets.append((sheet.attrib.get('name'), sheet.attrib.get('sheetId')))

        out.write("# Sheets in workbook:\n")
        for name, sid in sheets:
            out.write(f"- {name} (ID: {sid})\n")

        out.write("\n# Content Summary\n")
        for i, (name, sid) in enumerate(sheets):
            if i >= 10: break
            try:
                with z.open(f'xl/worksheets/sheet{i+1}.xml') as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    ns = {'ns': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
                    out.write(f"\n## Sheet: {name}\n")
                    rows = root.findall('.//ns:row', ns) if ns else root.findall('.//row')
                    for r_idx, row in enumerate(rows):
                        if r_idx >= 50:
                            out.write("  ... (truncated)\n")
                            break
                        row_data = []
                        cells = row.findall('.//ns:c', ns) if ns else row.findall('.//c')
                        for cell in cells:
                            t = cell.attrib.get('t')
                            v = cell.find('ns:v', ns) if ns else cell.find('v')
                            val = v.text if v is not None else ""
                            if t == 's' and val.isdigit():
                                val = shared_strings[int(val)]
                            row_data.append(val)
                        if any(row_data):
                            out.write(" | ".join([str(x).replace('\n', ' ') for x in row_data]) + "\n")
            except Exception as e:
                out.write(f"Error reading {name}: {e}\n")
    out.close()

if __name__ == '__main__':
    read_excel(sys.argv[1])
