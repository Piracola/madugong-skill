const fs = require('fs');
const path = require('path');

const { publishRoot, repoRoot, syncPublishSkill } = require('./sync-publish-skill');

const releaseRoot = path.join(repoRoot, 'release');
const releaseBranchName = 'release';

function ensureDirectoryExists(targetPath) {
  if (!fs.existsSync(targetPath) || !fs.statSync(targetPath).isDirectory()) {
    throw new Error(`Expected directory to exist: ${targetPath}`);
  }
}

function resetDirectory(targetPath) {
  fs.rmSync(targetPath, { recursive: true, force: true });
  fs.mkdirSync(targetPath, { recursive: true });
}

function copyPublishContentsToRelease() {
  ensureDirectoryExists(publishRoot);
  resetDirectory(releaseRoot);

  for (const entry of fs.readdirSync(publishRoot)) {
    fs.cpSync(path.join(publishRoot, entry), path.join(releaseRoot, entry), { recursive: true });
  }

  console.log(`Prepared release branch contents in ${releaseRoot}`);
  console.log('Next steps:');
  console.log(`1. git switch ${releaseBranchName} (create it once if needed)`);
  console.log(`2. copy the contents of ${releaseRoot} to the repository root of that branch`);
  console.log('3. commit and push the updated release branch');
}

function main() {
  syncPublishSkill();
  copyPublishContentsToRelease();
}

if (require.main === module) {
  main();
}

module.exports = {
  releaseBranchName,
  releaseRoot,
  copyPublishContentsToRelease,
};
