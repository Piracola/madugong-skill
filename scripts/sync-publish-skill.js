const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..');
const sourceRoot = path.join(repoRoot, '.claude', 'skills', 'madugong-perspective');
const publishRoot = path.join(repoRoot, 'publish', 'madugong-perspective');

const entriesToCopy = [
  'SKILL.md',
  'fewshots.md',
  'references',
];

function ensureSourceExists(targetPath) {
  if (!fs.existsSync(targetPath)) {
    throw new Error(`Missing source path: ${targetPath}`);
  }
}

function copyEntry(relativePath) {
  const sourcePath = path.join(sourceRoot, relativePath);
  const targetPath = path.join(publishRoot, relativePath);

  ensureSourceExists(sourcePath);
  fs.cpSync(sourcePath, targetPath, { recursive: true });
}

function syncPublishSkill() {
  ensureSourceExists(sourceRoot);

  fs.rmSync(publishRoot, { recursive: true, force: true });
  fs.mkdirSync(publishRoot, { recursive: true });

  for (const entry of entriesToCopy) {
    copyEntry(entry);
  }

  fs.copyFileSync(path.join(repoRoot, 'README.md'), path.join(publishRoot, 'README.md'));

  console.log(`Synced flat publish package to ${publishRoot}`);
}

if (require.main === module) {
  syncPublishSkill();
}

module.exports = {
  repoRoot,
  publishRoot,
  syncPublishSkill,
};
