import { useRef, useEffect } from "react";

const DRAWIO_ORIGIN = "https://embed.diagrams.net";

/* ------------------------------------------------------------------ */
/* Draw.io diagram viewer/editor — uses postMessage to load XML into  */
/* an iframe (avoids URL length limits on large diagrams)             */
/* ------------------------------------------------------------------ */
export default function DrawioDiagram({
  xml,
  editor = false,
  title = "Architecture Diagram",
}: {
  xml: string;
  editor?: boolean;
  title?: string;
}) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const xmlRef = useRef(xml);
  xmlRef.current = xml;

  useEffect(() => {
    const handler = (evt: MessageEvent) => {
      /* Accept messages from the embed origin and this iframe only */
      if (evt.origin !== DRAWIO_ORIGIN) return;
      if (evt.source !== iframeRef.current?.contentWindow) return;
      let msg: any;
      try {
        msg = typeof evt.data === "string" ? JSON.parse(evt.data) : evt.data;
      } catch {
        return; /* ignore non-JSON messages */
      }
      if (msg.event === "init" && iframeRef.current?.contentWindow) {
        iframeRef.current.contentWindow.postMessage(
          JSON.stringify({
            action: "load",
            xml: xmlRef.current,
            noSaveBtn: 1,
            noExitBtn: 1,
          }),
          DRAWIO_ORIGIN
        );
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);

  /* If xml changes after init already fired, send a new load */
  const prevXml = useRef(xml);
  useEffect(() => {
    if (xml && xml !== prevXml.current) {
      prevXml.current = xml;
      if (iframeRef.current?.contentWindow) {
        iframeRef.current.contentWindow.postMessage(
          JSON.stringify({ action: "load", xml }),
          DRAWIO_ORIGIN
        );
      }
    }
  }, [xml]);

  return (
    <iframe
      ref={iframeRef}
      title={editor ? `${title} Editor` : title}
      src={editor
        ? `${DRAWIO_ORIGIN}/?embed=1&proto=json&spin=1&libraries=1&noSaveBtn=1&noExitBtn=1&saveAndExit=0`
        : `${DRAWIO_ORIGIN}/?embed=1&proto=json&spin=1&ui=min&noSaveBtn=1&noExitBtn=1&saveAndExit=0`}
      style={{ width: "100%", height: editor ? "75vh" : 600, border: "1px solid #e9ebed", borderRadius: 4 }}
    />
  );
}
