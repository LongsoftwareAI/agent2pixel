/** Restrict host routing to an absolute local path, never an external URL. */
export function officeBase(value = '/office/'): string {
 if (!/^\/(?:[A-Za-z0-9_-]+\/)*$/.test(value)) throw new Error('AGENTVERSE_OFFICE_BASE must be an absolute path ending with /');
 return value;
}
/** Audited upstream uses root-relative public assets. Adapt at build time without altering vendor files. */
export function officeAssetPaths(source: string, base: string): string {
 return source.replace(/(["'`])\/assets\//g, `$1${base}assets/`);
}
