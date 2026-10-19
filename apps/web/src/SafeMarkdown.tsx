import { Fragment, type ReactNode } from 'react';
function inline(text: string): ReactNode[] {
    return text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g).map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**'))
            return <strong key={i}>
    {part.slice(2, -2)}
            </strong>;
        if (part.startsWith('`') && part.endsWith('`'))
            return <code key={i}>
    {part.slice(1, -1)}
            </code>;
        const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
        if (link) {
            let safe = false;
            try {
                const url = new URL(link[2]);
                safe = ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password;
            }
            catch { /* Invalid URL remains text. */ }
            if (safe)
                return <a key={i} href={link[2]} target="_blank" rel="noopener noreferrer">
    {link[1]} ↗</a>;
        }
        return <Fragment key={i}>
    {part}
        </Fragment>;
    });
}
export function SafeMarkdown({ content }: {
    content: string;
}) {
    const lines = content.split('\n'), blocks: ReactNode[] = [];
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.startsWith('```')) {
            const code = [];
            while (++i < lines.length && !lines[i].startsWith('```'))
                code.push(lines[i]);
            blocks.push(<pre key={i}>
    <code>
        {code.join('\n')}
    </code>
            </pre>);
            continue;
        }
        if (line.includes('|') && /^\s*\|?[\s:|-]+\|/.test(lines[i + 1] ?? '')) {
            const headers = line.split('|').map(x => x.trim()).filter(Boolean), body: string[][] = [];
            i += 2;
            for (; i < lines.length && lines[i].includes('|'); i++)
                body.push(lines[i].replace(/^\||\|$/g, '').split('|').map(x => x.trim()));
            i--;
            blocks.push(<details className="c-report-table" open key={i}>
    <summary>Bảng kết quả · {body.length} dòng</summary>
    <div>
        <table>
            <thead>
                <tr>
                    {headers.map((h, j) => <th key={j}>
                        {inline(h)}
                    </th>)}
                </tr>
            </thead>
            <tbody>
                {body.map((row, j) => <tr key={j}>
                    {row.map((cell, k) => <td key={k}>
                        {inline(cell)}
                    </td>)}
                </tr>)}
            </tbody>
        </table>
    </div>
            </details>);
            continue;
        }
        if (/^#{1,4}\s/.test(line)) {
            blocks.push(<h3 key={i}>
    {inline(line.replace(/^#+\s/, ''))}
            </h3>);
            continue;
        }
        if (/^[-*]\s/.test(line)) {
            blocks.push(<p className="c-markdown-list" key={i}>• {inline(line.slice(2))}
            </p>);
            continue;
        }
        blocks.push(line ? <p key={i}>
    {inline(line)}
        </p> : <br key={i}/>);
    }
    return <div className="c-markdown">
    {blocks}
    </div>;
}
