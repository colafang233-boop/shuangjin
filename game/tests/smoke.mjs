import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';

const root = path.resolve(import.meta.dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const loader = fs.readFileSync(path.join(root, 'loader.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'styles.css'), 'utf8');
const parts = Array.from({ length: 9 }, (_, index) =>
  fs.readFileSync(path.join(root, 'parts', `game-${String(index).padStart(2, '0')}.part.txt`), 'utf8'),
);
const js = parts.join('\n');
const rebuiltPath = path.join(root, '.smoke-rebuilt-game.js');
fs.writeFileSync(rebuiltPath, js);

try {
  execFileSync(process.execPath, ['--check', rebuiltPath], { stdio: 'inherit' });

  const checks = [
    ['HTML 引用样式表', html.includes('href="styles.css"')],
    ['HTML 引用加载器', html.includes('src="loader.js"')],
    ['Canvas 存在', html.includes('id="game"')],
    ['加载器包含全部九段源码', parts.every((_, index) => loader.includes(`game-${String(index).padStart(2, '0')}.part.txt`))],
    ['方向键映射存在', js.includes("arrowup: 'w'") && js.includes("arrowright: 'd'")],
    ['E/Enter/空格推进对话', js.includes("['enter', 'e', ' ']" )],
    ['持续 E 交互节流存在', js.includes('interactionRepeatCooldown')],
    ['墙体和迷宫障碍可绘制', js.includes('drawBox(box)') && js.includes("kind: 'obstacle'")],
    ['三道封印存在', js.includes('seals: [false, false, false]')],
    ['Boss 与双结局存在', js.includes('class Boss') && js.includes('resolveEndingChoice')],
    ['样式文件非空', css.length > 1000],
  ];

  for (const [name, passed] of checks) {
    assert.equal(passed, true, `失败：${name}`);
    console.log(`✓ ${name}`);
  }

  console.log(`\n${checks.length}/${checks.length} smoke checks passed.`);
} finally {
  fs.rmSync(rebuiltPath, { force: true });
}
