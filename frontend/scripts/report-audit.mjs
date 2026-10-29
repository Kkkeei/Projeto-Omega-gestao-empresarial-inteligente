import { spawnSync } from 'node:child_process';

const result = spawnSync('npm', ['audit', '--json'], { encoding: 'utf8', shell: process.platform === 'win32' });
let report;
try {
  report = JSON.parse(result.stdout || '{}');
} catch {
  console.log('npm audit returned no JSON report:', (result.stderr || result.stdout || '').slice(0, 2000));
  process.exit(0);
}
console.log('NPM_AUDIT_SUMMARY=' + JSON.stringify(report.metadata?.vulnerabilities || {}));
for (const [name, vulnerability] of Object.entries(report.vulnerabilities || {})) {
  console.log('NPM_AUDIT_PACKAGE=' + JSON.stringify({
    name,
    severity: vulnerability.severity,
    range: vulnerability.range,
    fixAvailable: vulnerability.fixAvailable,
    advisories: (vulnerability.via || []).map(item => typeof item === 'string' ? item : ({
      name: item.name,
      title: item.title,
      url: item.url,
      severity: item.severity,
      range: item.range,
    })),
  }));
}
