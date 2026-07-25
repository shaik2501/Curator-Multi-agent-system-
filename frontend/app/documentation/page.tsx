import fs from "fs";
import path from "path";
import DocumentationClient, {
  type DocSection,
} from "@/components/documentation/documentation-client";

// Read the docs fresh on every request rather than baking them in at build
// time — they can change independently of a frontend deploy.
export const dynamic = "force-dynamic";

const FILES: { file: string; label: string }[] = [
  { file: "01-OVERVIEW.md", label: "Overview" },
  { file: "02-ARCHITECTURE.md", label: "Architecture" },
  { file: "03-REQUIREMENTS.md", label: "Requirements" },
  { file: "04-UI-DESIGN.md", label: "UI Design" },
  { file: "05-BUILD-PLAN.md", label: "Build Plan" },
];

function readDocs(): DocSection[] {
  const docsDir = path.join(process.cwd(), "..", "docs");
  return FILES.map(({ file, label }) => {
    const fullPath = path.join(docsDir, file);
    let content: string | null = null;
    try {
      content = fs.readFileSync(fullPath, "utf-8");
    } catch {
      content = null;
    }
    return {
      id: file.replace(/\.md$/, "").toLowerCase(),
      file,
      label,
      content,
    };
  });
}

export default function DocumentationPage() {
  const sections = readDocs();
  return <DocumentationClient sections={sections} />;
}
