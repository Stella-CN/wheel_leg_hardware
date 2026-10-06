/** Procurement workbook for the V8.3 unpowered printed assembly trial.
 * Uses only the frozen V8.2 hardware BOM and the explicit ownership instruction.
 * Custom parts are supplied by the printing manifest, never charged twice here.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const root = path.resolve(import.meta.dirname, '..');
const outputDir = path.join(root, 'mechanical/v8_3_print_trial');
const sourcePath = path.join(root, 'mechanical/v8_2/bom_master.json');
const sourceText = await fs.readFile(sourcePath, 'utf8');
const source = JSON.parse(sourceText);
const runtime = path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies');
const workDir = path.join(root, 'tmp/v83_fitprint_bom');
await fs.mkdir(workDir, { recursive: true });
try { await fs.symlink(path.join(runtime, 'node/node_modules'), path.join(workDir, 'node_modules'), 'dir'); }
catch (error) { if (error.code !== 'EEXIST') throw error; }
const require = createRequire(path.join(workDir, 'package.json'));
const { Workbook, SpreadsheetFile } = await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const standard = source.rows.filter(r => ['标准件', '厂家目录件'].includes(r.supply_type));
const owned = source.rows.filter(r => r.supply_type === '外购设备' && r.id !== 'E08');
const unresolved = source.rows.filter(r => r.id === 'E08' || ['外购耗材', '待选型附件'].includes(r.supply_type));
const printed = source.rows.filter(r => ['定制金属件', '3D打印件'].includes(r.supply_type));
assert.equal(standard.length, 23);
assert.equal(standard.reduce((sum, r) => sum + r.quantity, 0), 274);
assert.equal(owned.length, 12);
assert.equal(printed.length, 38);
assert.equal(standard.length + owned.length + unresolved.length + printed.length, source.rows.length);
assert.equal(new Set(standard.map(r => r.standard_key)).size, standard.length);

const shortNotes = {
  LH01: '同规格合并，含轮辋 12 枚；按实际安装位置分装。',
  LH02: 'OA 到转子需此长度；不可换 M3×8。',
  LH03: '必须小头 Ø4.5×2；普通 M3 圆柱头不适配。',
  LH04: '法兰侧锁紧；必须小头 Ø4.5×2。',
  LH05: '轴承压盖 18 枚、轴销防脱 12 枚；TX4 工具。',
  LH06: '头 Ø6×1.7；不能直接换大头 ISO10642。',
  LH07: '头 Ø6×1.7；用于髋电机定子。',
  LH08: '头 Ø8×2.3；每腿 4 枚，勿重复计机身。',
  LH09: '每个 M4 接口一片，维持原厚度。',
  LH10: '配 M4 沉头螺钉，不换高型防松螺母。',
  LH11: '每髋 3 枚；打印孔清孔后轻装，禁止强压。',
  LH12: 'A/B/C 各 1 个/腿；不要换 C3/MC3 游隙。',
  BH01: '头 Ø6×1.7，90°；不要直接换大头 ISO10642。',
  BH03: '含后充电安装板紧固件。',
  BH04: '含电气安装架到托盘的紧固件。',
  BH05: '显示器托夹及机壳连接。',
  BH06: '光头外径 ≤4.5、高 ≤2.5，内六角 2。',
  BH07: 'AF5.5、厚 ≤2.4；不换高型尼龙防松螺母。',
  BH08: 'AF5、厚 ≤2；不换高型尼龙防松螺母。',
  BH09: '4 片为规定分压垫圈，不用于补长度。',
  EH01: '裸板 USB2CAN 用 4 枚，先核对工具空间。',
  EH02: '裸板 USB2CAN 用；AF3.2、厚1.3。',
  EH03: '配电板用；光头外径 ≤4.5。',
};
const pendingNotes = {
  E08: '仅装配试放可暂缺；要装轮胎时核实在手型号与轮辋匹配。',
  C01: '接触显示器金属边框，压缩后厚0.5；不可压玻璃。',
  C02: '用于固定已有电池；厚≤1，搭接与扣头避开 DC 口。',
  C03: '压缩后装配间隙0.5；仅压非接口壳边。',
  C04: '可留至走线试装；支持 USB3 数据，实际插头尺寸待核对。',
  T01: '本阶段断电试装可延后；额定电流与 DC 分断方案未确定。',
  T02: '本阶段可延后；安装板仅导孔，先选母座再定最终孔。',
  T03: '本阶段可延后；数量/针脚/长度待实际配线，不按 0 处理。',
  T04: '本阶段可延后；打印件不套用金属拧紧扭矩或未验证胶水。',
  T05: '本阶段可延后；护线套型号及开合方式仍需按插头确定。',
};
const purchaseData = standard.map(r => ({
  ...r, phase: '断电装配试装', inventory: 0, spare_quantity: 0,
  purchase_quantity: r.quantity, purchase_status: '补齐标准件',
  trial_note: shortNotes[r.id] ?? r.notes,
}));
const ownedData = owned.map(r => ({
  ...r, phase: '已有设备核对', ownership: '用户已确认已有',
  purchase_quantity: 0, trial_note: '使用在手实物试装；随设备自带零件不重复采购。',
}));
const unresolvedData = unresolved.map(r => ({
  ...r, phase: ['E08', 'C01', 'C02', 'C03'].includes(r.id) ? '按实物试装核实' : '走线或后续通电',
  inventory: null, spare_quantity: 0, purchase_quantity: null,
  purchase_status: r.quantity === null ? '数量及规格待定' : r.supply_type === '待选型附件' ? '先选型并核实库存' : '库存待核实',
  trial_note: pendingNotes[r.id] ?? r.notes,
}));
const alternative = {
  id: 'LC05-ALT', original_id: 'LC05', name: '轴销防脱挡片同尺寸薄片替代',
  spec: '外径9 / 孔2.2 / 厚0.20 mm', quantity_if_selected: 12,
  default_selected: false, default_purchase_quantity: 0,
  note: '原 LC05 仍在打印清单；0.2 mm 仅单层，易翘曲或破损。断电试装可改用同尺寸0.20 mm PET片或钢片，替换12片，不叠加；不得用更厚标准垫圈。',
};
const optionalAlternatives = [
  { id: 'LC01-ALT', original_id: 'LC01', name: '轴承外圈压盖', spec: 'Ø28/Ø16.8×0.8；3-Ø2.2 PCD24', quantity_if_selected: 6, default_purchase_quantity: 0, default_selected: false, note: '打印翘曲时用同厚片料按原孔阵列制作；与打印件二选一。' },
  { id: 'LC02-ALT', original_id: 'LC02', name: '关节轴销', spec: 'Ø6×14.05；双端M2×0.4', quantity_if_selected: 6, default_purchase_quantity: 0, default_selected: false, note: 'STL仅有底孔，打印后需手攻牙。无牙光杆只能检查同轴，不能等效防脱；按需同尺寸加工。' },
  { id: 'LC03-ALT', original_id: 'LC03', name: '内侧带肩衬套', spec: 'Ø8/Ø6.05×2.5＋肩Ø8.4/Ø6.2×1.25', quantity_if_selected: 6, default_purchase_quantity: 0, default_selected: false, note: '微小凸肩/间隙不适合用FDM判断精配；需要精配验收时才用同尺寸铜套。' },
  { id: 'LC04-ALT', original_id: 'LC04', name: '外侧带肩衬套', spec: '肩Ø8.4/Ø6.2×1.70＋Ø8/Ø6.05×2.5', quantity_if_selected: 6, default_purchase_quantity: 0, default_selected: false, note: '微小凸肩/间隙不适合用FDM判断精配；需要精配验收时才用同尺寸铜套。' },
  alternative,
  { id: 'LC06-ALT', original_id: 'LC06', name: 'OA限位肩销', spec: 'M3×3；Ø4肩长4.2；Ø7×1头', quantity_if_selected: 2, default_purchase_quantity: 0, default_selected: false, note: 'STL名义外圆不含真实牙；可观察限位位置。普通M3螺钉不能等效；按需同尺寸加工。' },
];

const wb = Workbook.create();
const stdSheet = wb.worksheets.add('标准件采购');
const pendingSheet = wb.worksheets.add('其他物料核实');
const ownedSheet = wb.worksheets.add('已有设备核对');
const FONT = 'Arial';
const FIRST = 9;
const widths = [10, 26, 48, 23, 10, 10, 10, 12, 24];
function col(n) { let s = ''; while (n) { n--; s = String.fromCharCode(65 + n % 26) + s; n = Math.floor(n / 26); } return s; }
function setup(sheet, title, subtitle, headers, ws, rowCount, tableName) {
  const last = FIRST + rowCount - 1;
  const end = col(headers.length);
  sheet.showGridLines = false;
  sheet.getRange(`A1:${end}${last}`).format.font = { name: FONT, size: 11, color: '#25323D' };
  sheet.getRange(`A1:${end}${last}`).format.verticalAlignment = 'center';
  sheet.getRange('A2').values = [[title]];
  sheet.getRange('A2').format.font = { name: FONT, size: 16, bold: true, color: '#223E52' };
  sheet.getRange(`A3:${end}3`).format.borders = { bottom: { style: 'thin', color: '#A6B4BE' } };
  sheet.getRange('A4').values = [[subtitle]];
  sheet.getRange('A4').format.font = { name: FONT, size: 11, color: '#4E5E69' };
  sheet.getRange('A6').values = [['来源：V8.2 完整 BOM；本次按单台、断电机械试装整理。']];
  sheet.getRange('A7').values = [['黄色为可编辑数量，空白表示尚未核实。件数不等于采购包装数。']];
  sheet.getRange('A6:A7').format.font = { name: FONT, size: 10, color: '#5E6B75' };
  sheet.getRange(`A8:${end}8`).values = [headers];
  sheet.getRange(`A8:${end}8`).format = {
    fill: '#294459', font: { name: FONT, size: 11, bold: true, color: '#FFFFFF' },
    horizontalAlignment: 'center', verticalAlignment: 'center', rowHeight: 28,
    borders: { insideVertical: { style: 'thin', color: '#FFFFFF' } },
  };
  for (let i = 0; i < ws.length; i++) sheet.getRange(`${col(i + 1)}1:${col(i + 1)}${last}`).format.columnWidth = ws[i];
  sheet.getRange(`A${FIRST}:${end}${last}`).format.wrapText = true;
  sheet.getRange(`A${FIRST}:${end}${last}`).format.rowHeight = 53;
  const table = sheet.tables.add(`A8:${end}${last}`, true, tableName);
  table.style = 'TableStyleMedium2';
  table.showFilterButton = true;
  sheet.freezePanes.freezeRows(8);
  sheet.freezePanes.freezeColumns(2);
  sheet.tabColor = '#294459';
  return last;
}
function putNotes(sheet, data, last) {
  sheet.getRange(`K8:K${last}`).format.columnWidth = 90;
  sheet.getRange('K8').values = [['装配与采购注意']];
  sheet.getRange('K8').format.font = { name: FONT, size: 11, bold: true, color: '#294459' };
  sheet.getRange(`K${FIRST}:K${last}`).values = data.map(r => [r.trial_note]);
  sheet.getRange(`K${FIRST}:K${last}`).format.font = { name: FONT, size: 11, color: '#445561' };
  sheet.getRange(`K${FIRST}:K${last}`).format.wrapText = false;
  for (let i = 0; i < data.length; i++) {
    wb.notes.add({
      id: `${sheet.name}:C${FIRST + i}`, authorId: '', createdAt: '',
      target: { cell: { sheetName: sheet.name, sheetId: sheet.sheetId, address: `C${FIRST + i}` } },
      body: { plainText: `来源：V8.2 BOM ${data[i].id}\n${data[i].source}\n原规格说明：${data[i].notes}` },
    });
  }
}
function numericInputs(sheet, start, end, columns) {
  for (const c of columns) {
    const range = sheet.getRange(`${c}${start}:${c}${end}`);
    range.format.fill = '#FFF0BE';
    range.setNumberFormat('0');
    range.dataValidation = { rule: { type: 'whole', operator: 'between', formula1: 0, formula2: 10000 } };
  }
}

const stdLast = setup(stdSheet, 'V8.3 打印试装标准件采购',
  '定制结构件全部由打印包提供；这里只采购真实螺钉、螺母、垫圈、销和轴承。',
  ['ID', '零件', '采购规格', '材料/等级', '需求/件', '在手/件', '备件/件', '需购买/件', '使用模块'],
  widths, purchaseData.length, 'TrialStandardParts');
stdSheet.getRange(`A${FIRST}:I${stdLast}`).values = purchaseData.map(r => [r.id, r.name, r.spec, r.material, r.quantity, 0, 0, null, r.module]);
numericInputs(stdSheet, FIRST, stdLast, ['F', 'G']);
stdSheet.getRange(`E${FIRST}:H${stdLast}`).setNumberFormat('0');
for (let i = FIRST; i <= stdLast; i++) {
  stdSheet.getRange(`H${i}`).formulas = [[`=IF(AND(ISNUMBER(F${i}),ISNUMBER(G${i})),MAX(0,E${i}+G${i}-F${i}),"待核实")`]];
}
stdSheet.getRange('E5:G5').values = [['需求总件数', 274, '需购总件数']];
stdSheet.getRange('H5').formulas = [[`=IF(COUNT(H${FIRST}:H${stdLast})=${purchaseData.length},SUM(H${FIRST}:H${stdLast}),"待核实")`]];
stdSheet.getRange('I5').values = [[`${purchaseData.length} 类`]];
putNotes(stdSheet, purchaseData, stdLast);

const pendLast = setup(pendingSheet, '其他物料与待选型项',
  '轮胎和耗材库存尚未确认；未确定规格的项目先核实，不按确定商品下单。',
  ['ID', '物料', '规格或已知尺寸', '本阶段安排', '需求', '在手', '备件', '待补数量', '核实状态'],
  widths, unresolvedData.length, 'TrialPendingParts');
pendingSheet.getRange(`A${FIRST}:I${pendLast}`).values = unresolvedData.map(r => [r.id, r.name, r.spec, r.phase, r.quantity ?? '待定', null, 0, null, r.purchase_status]);
numericInputs(pendingSheet, FIRST, pendLast, ['F', 'G']);
pendingSheet.getRange(`E${FIRST}:H${pendLast}`).setNumberFormat('0');
for (let i = FIRST; i <= pendLast; i++) {
  pendingSheet.getRange(`H${i}`).formulas = [[`=IF(ISNUMBER(E${i}),IF(AND(ISNUMBER(F${i}),ISNUMBER(G${i})),MAX(0,E${i}+G${i}-F${i}),"待核实"),"待定")`]];
  const item = unresolvedData[i - FIRST];
  if (item.supply_type === '待选型附件') {
    pendingSheet.getRange(`I${i}`).values = [[item.quantity === null ? '数量及规格待定' : '规格仍待选型']];
  } else {
    pendingSheet.getRange(`I${i}`).formulas = [[`=IF(ISNUMBER(H${i}),IF(H${i}>0,"需补齐数量","数量已齐"),"库存待核实")`]];
  }
}
pendingSheet.getRange(`H${FIRST}:I${pendLast}`).conditionalFormats.add('containsText', { text: '待', format: { font: { color: '#8A5C12' } } });
putNotes(pendingSheet, unresolvedData, pendLast);
const altRow = pendLast + 3;
pendingSheet.getRange(`A${altRow}`).values = [['可选替代，仅打印失败后启用']];
pendingSheet.getRange(`A${altRow}`).format.font = { name: FONT, size: 12, bold: true, color: '#294459' };
pendingSheet.getRange(`A${altRow + 1}:I${altRow + 7}`).values = [
  ['对应ID', '精细定制件', '必须保持的尺寸', '替代条件', '替代用量', '单位', '默认购买', '原打印件', '采购方式'],
  ...optionalAlternatives.map(r => [r.original_id, r.name, r.spec, '按打印试装结果', r.quantity_if_selected, '件', 0, '保留在打印清单', '按原图定制']),
];
pendingSheet.getRange(`A${altRow + 1}:I${altRow + 7}`).format.font = { name: FONT, size: 11, color: '#25323D' };
pendingSheet.getRange(`A${altRow + 1}:I${altRow + 1}`).format.font = { name: FONT, size: 11, bold: true, color: '#294459' };
pendingSheet.getRange(`A${altRow + 1}:I${altRow + 7}`).format.rowHeight = 53;
pendingSheet.getRange(`A${altRow + 1}:I${altRow + 7}`).format.wrapText = true;
pendingSheet.getRange(`K${altRow + 2}:K${altRow + 7}`).values = optionalAlternatives.map(r => [r.note]);
pendingSheet.getRange(`K${altRow + 2}:K${altRow + 7}`).format.font = { name: FONT, size: 11, color: '#445561' };
pendingSheet.getRange(`K${altRow + 2}:K${altRow + 7}`).format.wrapText = false;
pendingSheet.getRange(`K${altRow + 2}:K${altRow + 7}`).format.columnWidth = 118;

const ownLast = setup(ownedSheet, '已有电机与电子模块核对',
  '用户已确认已有这些设备，使用实物装配；本表仅核对数量与版本，不重复采购。',
  ['ID', '设备', '型号与安装包络', '在手状态', '整机需求', '单位', '本次采购', '核对结果', '模块'],
  widths, ownedData.length, 'TrialOwnedEquipment');
ownedSheet.getRange(`A${FIRST}:I${ownLast}`).values = ownedData.map(r => [r.id, r.name, r.spec, r.ownership, r.quantity, r.unit, 0, '待实物核对', r.module]);
ownedSheet.getRange(`E${FIRST}:G${ownLast}`).setNumberFormat('0');
ownedSheet.getRange(`H${FIRST}:H${ownLast}`).format.fill = '#FFF0BE';
ownedSheet.getRange(`H${FIRST}:H${ownLast}`).dataValidation = { rule: { type: 'list', values: ['待实物核对', '一致', '数量不符', '版本不符'] } };
ownedSheet.getRange('A7').values = [['黄色仅记录核对结果；本次采购始终为 0，缺件需另行确认。']];
putNotes(ownedSheet, ownedData, ownLast);

const tests = [];
const value = (sheet, address) => sheet.getRange(address).values[0][0];
function check(description, actual, expected) { assert.equal(actual, expected, description); tests.push({ description, actual, expected }); }
wb.recalculate();
check('标准件总量', value(stdSheet, 'H5'), 274);
for (const i of [0, 11, standard.length - 1]) {
  const r = FIRST + i; const qty = standard[i].quantity;
  stdSheet.getRange(`F${r}:G${r}`).values = [[2, 3]];
  wb.recalculate(); check(`${standard[i].id} 库存和备件`, value(stdSheet, `H${r}`), qty + 1);
  stdSheet.getRange(`F${r}:G${r}`).values = [[qty + 1, 0]];
  wb.recalculate(); check(`${standard[i].id} 库存足够`, value(stdSheet, `H${r}`), 0);
  stdSheet.getRange(`F${r}:G${r}`).values = [[null, 0]];
  wb.recalculate(); check(`${standard[i].id} 缺库存`, value(stdSheet, `H${r}`), '待核实');
  check(`${standard[i].id} 总计保持待核实`, value(stdSheet, 'H5'), '待核实');
  stdSheet.getRange(`F${r}:G${r}`).values = [[0, 0]];
}
const tireRow = FIRST + unresolved.findIndex(r => r.id === 'E08');
const unknownRow = FIRST + unresolved.findIndex(r => r.id === 'T01');
wb.recalculate();
check('轮胎库存未填', value(pendingSheet, `H${tireRow}`), '待核实');
pendingSheet.getRange(`F${tireRow}`).values = [[0]];
wb.recalculate(); check('轮胎库存明确为零', value(pendingSheet, `H${tireRow}`), 2);
check('轮胎库存状态同步', value(pendingSheet, `I${tireRow}`), '需补齐数量');
pendingSheet.getRange(`F${tireRow}`).values = [[2]];
wb.recalculate(); check('轮胎数量齐状态同步', value(pendingSheet, `I${tireRow}`), '数量已齐');
pendingSheet.getRange(`F${tireRow}`).values = [[null]];
pendingSheet.getRange(`F${unknownRow}`).values = [[0]];
wb.recalculate(); check('未知需求不能变零', value(pendingSheet, `H${unknownRow}`), '待定');
pendingSheet.getRange(`F${unknownRow}`).values = [[null]];
wb.recalculate();
check('还原标准件总量', value(stdSheet, 'H5'), 274);
check('已有设备不采购', ownedSheet.getRange(`G${FIRST}:G${ownLast}`).values.flat().reduce((a, b) => a + b, 0), 0);
const inspection = await wb.inspect({ kind: 'table', range: '标准件采购!E8:I13', include: 'values,formulas', tableMaxRows: 6, tableMaxCols: 5 });
const errorScan = await wb.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!', options: { useRegex: true, maxResults: 50 }, summary: '最终公式错误检查' });
const errorPattern = /^#(REF!|DIV\/0!|VALUE!|NAME\?|N\/A|NUM!|NULL!|SPILL!|CALC!)/;
for (const sheet of [stdSheet, pendingSheet, ownedSheet]) {
  for (const row of sheet.getUsedRange().values) for (const v of row) assert.ok(!errorPattern.test(String(v ?? '')), `${sheet.name}: ${v}`);
}
await fs.mkdir(path.join(outputDir, 'verification/bom'), { recursive: true });
const renderViews = [
  ['标准件采购', 'A1:I17', 'standard_top'], ['标准件采购', 'A18:I31', 'standard_bottom'],
  ['其他物料核实', `A1:I${pendLast}`, 'pending'],
  ['其他物料核实', `A${altRow}:I${altRow + 7}`, 'optional_alternatives'], ['已有设备核对', 'A1:I20', 'owned'],
];
for (const [sheetName, range, name] of renderViews) {
  const blob = await wb.render({ sheetName, range, scale: 1.5, format: 'png' });
  await fs.writeFile(path.join(outputDir, 'verification/bom', `${name}.png`), new Uint8Array(await blob.arrayBuffer()));
}
const workbookFile = await SpreadsheetFile.exportXlsx(wb);
await workbookFile.save(path.join(outputDir, '采购BOM.xlsx'));
const csvQuote = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
const csv = [['ID', '零件', '采购规格', '材料等级', '需求件数', '在手件数', '备件件数', '需购买件数', '模块', '注意事项'],
  ...purchaseData.map(r => [r.id, r.name, r.spec, r.material, r.quantity, 0, 0, r.quantity, r.module, r.trial_note])]
  .map(row => row.map(csvQuote).join(',')).join('\r\n');
await fs.writeFile(path.join(outputDir, '采购清单.csv'), '\uFEFF' + csv + '\r\n');
await fs.writeFile(path.join(outputDir, 'bom_purchase.json'), JSON.stringify({
  revision: 'V8.3-print-trial', source_revision: 'V8.2',
  source_bom_sha256: crypto.createHash('sha256').update(sourceText).digest('hex'),
  scope: '单台断电机械试装；标准件23类274件。所有定制结构打印，已有电机电子不再采购。',
  inventory_policy: '标准件默认在手0、备件0；轮胎及其他耗材库存未核实，保持null。',
  totals: { standard_types: standard.length, standard_pieces: 274, owned_equipment_types: owned.length, existing_custom_types: printed.length, existing_custom_pieces: printed.reduce((a, r) => a + r.quantity, 0) },
  standard_purchase: purchaseData, owned_equipment: ownedData, unresolved_materials: unresolvedData,
  optional_alternatives: optionalAlternatives,
  custom_parts_policy: '38类原定制零件及V8.3新增外观件的文件/数量以同包打印清单为准；不计本阶段CNC采购。',
}, null, 2));
await fs.writeFile(path.join(outputDir, 'verification/bom', 'workbook_qa.json'), JSON.stringify({
  standard_types: 23, standard_pieces: 274, source_rows_accounted: source.rows.length,
  covered_partition: { standard: standard.length, owned: owned.length, unresolved: unresolved.length, custom: printed.length },
  formula_tests: tests, formula_errors: [], inspection: inspection.ndjson, error_scan: errorScan.ndjson,
  verification_engine: '@oai/artifact-tool', native_excel_opened: false,
  inventory_defaults: 'Standard 0; spare 0; unresolved inventory blank',
}, null, 2));
console.log(JSON.stringify({ workbook: path.join(outputDir, '采购BOM.xlsx'), standard_types: 23, pieces: 274, formula_tests: tests.length, source_rows_accounted: source.rows.length }));
