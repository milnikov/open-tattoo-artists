import { splitTextWithLinks, type CopySection } from "@/lib/agent-surface";

function RichText({ text }: { text: string }) {
  return (
    <>
      {splitTextWithLinks(text).map((part, index) =>
        part.kind === "link" ? (
          <a
            key={`${part.value}-${index}`}
            href={part.value}
            className="text-foreground underline underline-offset-2 hover:text-muted-foreground"
          >
            {part.value}
          </a>
        ) : (
          <span key={`${index}-${part.value.slice(0, 12)}`}>{part.value}</span>
        ),
      )}
    </>
  );
}

export function CopySections({ sections }: { sections: CopySection[] }) {
  return (
    <>
      {sections.map((section) => {
        const Heading = section.level === 3 ? "h3" : "h2";
        return (
          <section key={section.heading}>
            <Heading className="text-sm font-semibold text-foreground mb-2">{section.heading}</Heading>
            {section.paragraphs.map((paragraph) => (
              <p key={paragraph} className="mb-2">
                <RichText text={paragraph} />
              </p>
            ))}
            {section.code?.map((block) => (
              <pre
                key={block}
                className="mb-3 overflow-x-auto rounded bg-secondary p-3 text-xs text-foreground"
              >
                <code>{block}</code>
              </pre>
            ))}
          </section>
        );
      })}
    </>
  );
}
