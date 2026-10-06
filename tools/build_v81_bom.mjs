/** Build the V8.1 procurement/manufacturing workbook from reviewed BOM JSON.
 * Usage: bundled-node tools/build_v81_bom.mjs <bom.json> [output-directory]
 * The source must set ready_for_workbook=true. Quantities are per whole robot.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const root = path.resolve(import.meta.dirname, '..');
const inputPath = path.resolve(process.argv[2] ?? path.join(root, 'mechanical/v8_1/bom_master.json'));
const outputDir = path.resolve(process.argv[3] ?? path.join(root, 'mechanical/v8_1'));
const runtime = path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies');
const workDir = path.join(root, 'tmp/v81_bom_workspace');
await fs.mkdir(workDir, { recursive: true });
try {
  await fs.symlink(path.join(runtime, 'node/node_modules'), path.join(workDir, 'node_modules'), 'dir');
} catch (error) {
  if (error.code !== 'EEXIST') throw error;
}
const dependencyRequire = createRequire(path.join(workDir, 'package.json'));
const { Workbook, SpreadsheetFile } = await import(pathToFileURL(dependencyRequire.resolve('@oai/artifact-tool')).href);
const sourceText = await fs.readFile(inputPath, 'utf8');
const source = JSON.parse(sourceText);
assert.equal(source.ready_for_workbook, true, 'Only build from reviewed, ready BOM JSON');
assert.ok(Array.isArray(source.rows) && source.rows.length, 'BOM must have nonempty rows');
const requiredFields = ['id', 'module', 'name', 'spec', 'unit', 'material', 'process', 'supply_type', 'source', 'status'];
const items = source.rows.map((item) => ({ ...item, notes: item.notes ?? '', standard_key: item.standard_key ?? '' }));
const ids = new Set();
for (const item of items) {
  for (const field of requiredFields) assert.ok(typeof item[field] === 'string' && item[field].trim(), `${item.id}: missing ${field}`);
  assert.ok(!ids.has(item.id), `Duplicate BOM ID ${item.id}`);
  ids.add(item.id);
  const unknownQuantity = item.quantity === null && item.supply_type === '待选型附件';
  assert.ok(unknownQuantity || (Number.isFinite(item.quantity) && item.quantity > 0), `${item.id}: invalid whole-robot quantity`);
  if (['标准件', '厂家目录件'].includes(item.supply_type)) assert.ok(item.standard_key, `${item.id}: procurement key required`);
}
const manufactured = items.filter((item) => item.supply_type === '定制金属件' || item.supply_type === '3D打印件');
const groups = new Map();
for (const item of items.filter((row) => row.standard_key)) {
  assert.ok(['标准件', '厂家目录件'].includes(item.supply_type), `${item.id}: custom item must not have a procurement key`);
  if (!groups.has(item.standard_key)) groups.set(item.standard_key, { first: item, quantity: 0, modules: new Set(), ids: [] });
  const group = groups.get(item.standard_key);
  for (const field of ['spec', 'material', 'unit', 'supply_type']) assert.equal(item[field], group.first[field], `Conflicting ${field} for ${item.standard_key}`);
  group.quantity += item.quantity;
  group.modules.add(item.module);
  group.ids.push(item.id);
}
const standardGroups = [...groups.entries()].sort(([a], [b]) => a.localeCompare(b, 'zh-CN'));
assert.ok(manufactured.length && standardGroups.length, 'Manufactured and standard parts must both be present');

const wb = Workbook.create();
const standard = wb.worksheets.add('标准与目录件');
const manufacturing = wb.worksheets.add('制造分类');
const bom = wb.worksheets.add('完整BOM');
const font = 'Arial';
const firstRow = 8;
const lastBom = firstRow + items.length - 1;
const lastManufacturing = firstRow + manufactured.length - 1;
const lastStandard = firstRow + standardGroups.length - 1;
const excelCol = (n) => {
  let result = '';
  while (n > 0) { n -= 1; result = String.fromCharCode(65 + (n % 26)) + result; n = Math.floor(n / 26); }
  return result;
};
function setup(sheet, title, note, columns, widths, rowCount, tableName) {
  const last = firstRow + rowCount - 1;
  const lastCol = excelCol(columns.length);
  sheet.showGridLines = false;
  sheet.getRange(`A1:${lastCol}${last}`).format.font = { name: font, size: 11, color: '#202B36' };
  sheet.getRange(`A1:${lastCol}${last}`).format.verticalAlignment = 'center';
  sheet.getRange('A2').values = [[title]];
  sheet.getRange('A2').format.font = { name: font, size: 16, bold: true, color: '#21374B' };
  sheet.getRange(`A3:${lastCol}3`).format.borders = { bottom: { style: 'thin', color: '#AAB7C2' } };
  sheet.getRange('A4').values = [[note]];
  sheet.getRange('A4').format.font = { name: font, size: 11, color: '#596873' };
  if (source.modules) {
    sheet.getRange('A6').values = [[Object.entries(source.modules).map(([key, value]) => `${key} ${value}`).join('；')]];
    sheet.getRange('A6').format.font = { name: font, size: 11, color: '#596873' };
  }
  sheet.getRange(`A7:${lastCol}7`).values = [columns];
  sheet.getRange(`A7:${lastCol}7`).format = {
    fill: '#294459', font: { name: font, size: 11, bold: true, color: '#FFFFFF' },
    horizontalAlignment: 'center', verticalAlignment: 'center', rowHeight: 30,
    borders: { insideVertical: { style: 'thin', color: '#FFFFFF' } },
  };
  sheet.getRange(`A${firstRow}:${lastCol}${last}`).format.wrapText = true;
  for (let col = 0; col < widths.length; col += 1) sheet.getRange(`${excelCol(col + 1)}1:${excelCol(col + 1)}${last}`).format.columnWidth = widths[col];
  const table = sheet.tables.add(`A7:${lastCol}${last}`, true, tableName);
  table.showFilterButton = true;
  table.style = 'TableStyleMedium2';
  sheet.freezePanes.freezeRows(7);
  sheet.freezePanes.freezeColumns(3);
  sheet.tabColor = '#294459';
}
function fitRows(sheet, rows, widths) {
  rows.forEach((row, index) => {
    const lines = Math.max(1, ...row.map((value, col) => {
      const chars = [...String(value ?? '')].reduce((sum, char) => sum + (char.codePointAt(0) > 255 ? 2 : 1), 0);
      return Math.ceil(chars / Math.max(4, widths[col] - 2));
    }));
    sheet.getRange(`A${firstRow + index}:${excelCol(widths.length)}${firstRow + index}`).format.rowHeight = Math.max(34, lines * 15 + 10);
  });
}

const bomColumns = ['零件ID', '装配模块', '零件名称', '完整规格', '单机数量', '单位', '材料/等级', '制造工艺', '供应方式', '状态', '来源', '备注', '标准采购键'];
const bomWidths = [17, 18, 29, 48, 10, 7, 20, 18, 15, 28, 44, 55, 30];
const bomRows = items.map((item) => [item.id, item.module, item.name, item.spec, item.quantity ?? '待定', item.unit, item.material, item.process, item.supply_type, item.status, item.source, item.notes, item.standard_key]);
setup(bom, 'V8.1 采购与制造 BOM', source.scope_note ?? '数量按整机计。左右件分别列出；定制销、隔套不计入标准件。', bomColumns, bomWidths, items.length, 'V81CompleteBOM');
bom.getRange(`A${firstRow}:M${lastBom}`).values = bomRows;
bom.getRange(`E${firstRow}:E${lastBom}`).setNumberFormat('0');
bom.getRange(`F${firstRow}:F${lastBom}`).format.horizontalAlignment = 'center';
bom.getRange(`J${firstRow}:J${lastBom}`).conditionalFormats.add('containsText', {
  text: '待', format: { fill: '#FFF1CC', font: { color: '#7F5200' } },
});
fitRows(bom, bomRows, bomWidths);
bom.getRange('A5').values = [[`来源版本：${source.revision ?? 'V8.1'}    日期：${source.date ?? '2026-09-28'}`]];
bom.getRange('J5').values = [['明细行数']];
bom.getRange('K5').formulas = [[`=COUNTA(A${firstRow}:A${lastBom})`]];

const manufacturingColumns = ['零件ID', '装配模块', '零件名称', '数量', '材料/等级', '制造工艺', '供应方式', '关键加工或装配要求', '状态'];
const manufacturingWidths = [17, 18, 31, 8, 22, 21, 15, 70, 37];
const manufacturingRows = manufactured.map((item) => [item.id, item.module, item.name, item.quantity, item.material, item.process, item.supply_type, item.manufacturing_notes ?? item.notes ?? item.spec, item.status]);
setup(manufacturing, '制造件分类', '按制造工艺筛选发包。钣金替代方案若未展开图验证，不作为当前可直接加工方案。', manufacturingColumns, manufacturingWidths, manufactured.length, 'V81Manufacturing');
manufacturing.getRange(`A${firstRow}:I${lastManufacturing}`).values = manufacturingRows;
// Quantities link to the authoritative source using IDs, so sorting either view is safe.
manufacturingRows.forEach((row, index) => {
  const r = firstRow + index;
  manufacturing.getRange(`D${r}`).formulas = [[`=SUMIFS('完整BOM'!$E$${firstRow}:$E$${lastBom},'完整BOM'!$A$${firstRow}:$A$${lastBom},A${r})`]];
});
manufacturing.getRange(`D${firstRow}:D${lastManufacturing}`).setNumberFormat('0');
fitRows(manufacturing, manufacturingRows, manufacturingWidths);

const standardColumns = ['标准采购键', '名称', '完整采购规格', '材料/等级', '单机用量', '单位', '备件比例', '备件数量', '建议购买量', '使用模块', '状态'];
const standardWidths = [28, 27, 53, 20, 10, 7, 12, 12, 14, 36, 36];
const standardRows = standardGroups.map(([key, group]) => [key, group.first.name, group.first.spec, group.first.material, group.quantity, group.first.unit, 0, 0, group.quantity, [...group.modules].join('、'), group.first.status]);
setup(standard, '标准与目录件采购汇总', '同规范、尺寸、等级和表面处理才合并。黄色备件比例可编辑，默认 0%，向上取整。', standardColumns, standardWidths, standardGroups.length, 'V81StandardProcurement');
standard.getRange(`A${firstRow}:K${lastStandard}`).values = standardRows;
for (let index = 0; index < standardGroups.length; index += 1) {
  const r = firstRow + index;
  standard.getRange(`E${r}`).formulas = [[`=SUMIFS('完整BOM'!$E$${firstRow}:$E$${lastBom},'完整BOM'!$M$${firstRow}:$M$${lastBom},A${r})`]];
  standard.getRange(`H${r}`).formulas = [[`=ROUNDUP(E${r}*G${r},0)`]];
  standard.getRange(`I${r}`).formulas = [[`=E${r}+H${r}`]];
}
standard.getRange(`G${firstRow}:G${lastStandard}`).format.fill = '#FFF1CC';
standard.getRange(`F${firstRow}:F${lastStandard}`).format.horizontalAlignment = 'center';
standard.getRange(`G${firstRow}:G${lastStandard}`).setNumberFormat('0%');
standard.getRange(`G${firstRow}:G${lastStandard}`).dataValidation = { rule: { type: 'decimal', operator: 'between', formula1: 0, formula2: 1 } };
for (const column of ['E', 'H', 'I']) standard.getRange(`${column}${firstRow}:${column}${lastStandard}`).setNumberFormat('0');
fitRows(standard, standardRows, standardWidths);

// Independently reconcile source quantities, then exercise editable spare-rate formulas.
wb.recalculate();
for (let index = 0; index < manufactured.length; index += 1) {
  assert.equal(manufacturing.getRange(`D${firstRow + index}`).values[0][0], manufactured[index].quantity);
}
for (let index = 0; index < standardGroups.length; index += 1) {
  const quantity = standardGroups[index][1].quantity;
  assert.equal(standard.getRange(`E${firstRow + index}`).values[0][0], quantity);
  assert.equal(standard.getRange(`I${firstRow + index}`).values[0][0], quantity);
}
const inputTests = [];
for (const index of [...new Set([0, Math.floor(standardGroups.length / 2), standardGroups.length - 1])]) {
  const r = firstRow + index;
  const quantity = standardGroups[index][1].quantity;
  for (const rate of [0, 0.1, 1]) {
    standard.getRange(`G${r}`).values = [[rate]];
    wb.recalculate();
    assert.equal(standard.getRange(`H${r}`).values[0][0], Math.ceil(quantity * rate));
    assert.equal(standard.getRange(`I${r}`).values[0][0], quantity + Math.ceil(quantity * rate));
    inputTests.push({ row: r, rate, spareQuantity: Math.ceil(quantity * rate), purchaseQuantity: quantity + Math.ceil(quantity * rate) });
  }
  standard.getRange(`G${r}`).values = [[0]];
}
wb.recalculate();
const formulaErrorPattern = /^#(REF!|DIV\/0!|VALUE!|NAME\?|N\/A|NUM!|NULL!|SPILL!|CALC!)/;
for (const sheet of [bom, manufacturing, standard]) {
  for (const row of sheet.getUsedRange().values) {
    for (const value of row) assert.ok(!formulaErrorPattern.test(String(value ?? '')), `Formula error in ${sheet.name}: ${value}`);
  }
}
const errors = await wb.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!', options: { useRegex: true, maxResults: 300 }, summary: 'BOM formula error scan' });
await fs.mkdir(outputDir, { recursive: true });
const previewDir = path.join(workDir, 'previews');
await fs.mkdir(previewDir, { recursive: true });
const inspections = {};
for (const [sheet, range, name] of [
  [bom, 'A1:J14', 'bom'],
  [manufacturing, 'A1:I15', 'manufacturing'],
  [standard, 'A1:K15', 'standard'],
  [bom, `A${lastBom - 7}:L${lastBom}`, 'bom_accessories'],
  [manufacturing, `A${lastManufacturing - 6}:I${lastManufacturing}`, 'manufacturing_details'],
  [standard, `A${lastStandard - 6}:K${lastStandard}`, 'catalogue'],
]) {
  inspections[name] = (await wb.inspect({ kind: 'table', range: `${sheet.name}!${range}`, include: 'values,formulas', tableMaxRows: 15, tableMaxCols: 11 })).ndjson;
  const preview = await wb.render({ sheetName: sheet.name, range, scale: 1.5, format: 'png' });
  await fs.writeFile(path.join(previewDir, `${name}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const requiredOutputDir = path.join(root, 'outputs/v81_bom_20260928');
await fs.mkdir(requiredOutputDir, { recursive: true });
const fileName = '采购与制造BOM.xlsx';
const result = await SpreadsheetFile.exportXlsx(wb);
await result.save(path.join(requiredOutputDir, fileName));
await fs.copyFile(path.join(requiredOutputDir, fileName), path.join(outputDir, fileName));
function csv(rows) {
  return '\uFEFF' + rows.map((row) => row.map((value) => `"${String(value ?? '').replaceAll('"', '""')}"`).join(',')).join('\r\n') + '\r\n';
}
await fs.writeFile(path.join(outputDir, 'BOM完整.csv'), csv([bomColumns, ...bomRows]));
await fs.writeFile(path.join(outputDir, '制造件分类.csv'), csv([manufacturingColumns, ...manufacturingRows]));
await fs.writeFile(path.join(outputDir, '标准与目录件采购汇总.csv'), csv([standardColumns, ...standardRows]));
const report = {
  source: inputPath, source_sha256: crypto.createHash('sha256').update(sourceText).digest('hex'),
  rows: items.length, manufactured_types: manufactured.length,
  manufactured_quantity: manufactured.reduce((sum, row) => sum + row.quantity, 0),
  standard_types: standardGroups.length,
  iso_din_standard_types: standardGroups.filter(([, group]) => group.first.supply_type === '标准件').length,
  manufacturer_catalogue_types: standardGroups.filter(([, group]) => group.first.supply_type === '厂家目录件').length,
  standard_quantity: standardGroups.reduce((sum, [, group]) => sum + group.quantity, 0),
  independent_quantity_reconciliation: true, spare_rate_10_percent_test: true, input_tests: inputTests,
  error_scan: errors.ndjson, inspections, render_directory: previewDir,
  renderer_review_required: true, native_excel_application_test: 'not performed; formulas evaluated with artifact-tool',
};
await fs.writeFile(path.join(outputDir, 'bom_workbook_review.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ workbook: path.join(outputDir, fileName), rows: items.length, standardTypes: standardGroups.length, previews: previewDir, errorScan: errors.ndjson }, null, 2));
