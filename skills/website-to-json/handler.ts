type Preset = "article" | "product_page" | "company_directory" | "docs_page";

declare const process: {
  env: Record<string, string | undefined>;
};

interface SkillInput {
  url: string;
  preset: Preset;
  locale?: string;
  include_sources?: boolean;
}

interface SkillResult {
  preset: Preset;
  url: string;
  data: Record<string, unknown>;
  confidence: number;
  source_coverage: number;
  field_confidence: Record<string, number>;
  source_urls: string[];
  warnings: string[];
}

interface PageData {
  url: string;
  canonicalUrl: string;
  host: string;
  title: string;
  description: string;
  html: string;
  text: string;
  links: string[];
  meta: Record<string, string>;
  jsonLd: Record<string, unknown>[];
}

type RequestHandler = (input: SkillInput) => Promise<SkillResult>;

const PRESET_FIELDS: Record<Preset, string[]> = {
  article: ["title", "author", "published_date", "summary", "canonical_url", "site_name"],
  product_page: ["product_name", "price", "currency", "availability", "description", "brand"],
  company_directory: [
    "company_name",
    "domain",
    "industry",
    "employee_range",
    "revenue_range",
    "hq_city",
    "hq_country",
    "linkedin_url",
    "founded_year",
  ],
  docs_page: ["doc_title", "section_count", "summary", "canonical_url", "product_name", "version"],
};

const EMPLOYEE_RANGE_BUCKETS = [
  { max: 10, label: "1-10" },
  { max: 50, label: "11-50" },
  { max: 200, label: "51-200" },
  { max: 500, label: "201-500" },
  { max: 1000, label: "501-1,000" },
  { max: 5000, label: "1,001-5,000" },
  { max: 10000, label: "5,001-10,000" },
  { max: Number.POSITIVE_INFINITY, label: "10,000+" },
];

const REVENUE_BUCKETS = [
  { max: 1000000, label: "<$1M" },
  { max: 10000000, label: "$1M-$10M" },
  { max: 50000000, label: "$10M-$50M" },
  { max: 100000000, label: "$50M-$100M" },
  { max: 500000000, label: "$100M-$500M" },
  { max: 1000000000, label: "$500M-$1B" },
  { max: Number.POSITIVE_INFINITY, label: "$1B+" },
];

const COUNTRY_ALIASES: Record<string, string> = {
  usa: "United States",
  us: "United States",
  "u.s.": "United States",
  unitedstates: "United States",
  unitedstatesofamerica: "United States",
  uk: "United Kingdom",
};

export default async function handler(input: SkillInput | Request): Promise<SkillResult | Response> {
  if (looksLikeRequest(input)) {
    return authMiddleware(input, extractWebsiteToJson);
  }

  return extractWebsiteToJson(validateInput(input));
}

export async function authMiddleware(request: Request, next: RequestHandler): Promise<Response> {
  try {
    enforceAuth(request);
    const rawBody = await request.json();
    const payload = validateInput(rawBody);
    const result = await next(payload);
    return successResponse(result);
  } catch (error) {
    return errorResponse(error);
  }
}

async function extractWebsiteToJson(input: SkillInput): Promise<SkillResult> {
  const page = await fetchPage(input.url);
  const sourceUrls = new Set<string>([page.url]);
  if (page.canonicalUrl && page.canonicalUrl !== page.url) {
    sourceUrls.add(page.canonicalUrl);
  }

  const extracted = extractPresetData(input.preset, page);
  const expectedFields = PRESET_FIELDS[input.preset];
  const presentFields = expectedFields.filter((field) => isMeaningful(extracted[field]));
  const sourceCoverage = round(presentFields.length / expectedFields.length, 2);
  const fieldConfidence = buildFieldConfidence(input.preset, extracted, page);
  const confidence = buildConfidence(input.preset, extracted, page, sourceCoverage);
  const warnings = buildWarnings(input.preset, extracted, page, input.locale);

  return {
    preset: input.preset,
    url: page.url,
    data: extracted,
    confidence,
    source_coverage: sourceCoverage,
    field_confidence: fieldConfidence,
    source_urls: input.include_sources === false ? [] : Array.from(sourceUrls),
    warnings,
  };
}

function extractPresetData(preset: Preset, page: PageData): Record<string, unknown> {
  switch (preset) {
    case "article":
      return extractArticle(page);
    case "product_page":
      return extractProduct(page);
    case "company_directory":
      return extractCompany(page);
    case "docs_page":
      return extractDocs(page);
    default:
      return {};
  }
}

function extractArticle(page: PageData): Record<string, unknown> {
  const articleLd = findJsonLd(page.jsonLd, ["Article", "NewsArticle", "BlogPosting"]);
  const author = readAuthor(articleLd, page);
  const publishedDate = firstNonEmpty(
    metaValue(page.meta, "article:published_time"),
    metaValue(page.meta, "date"),
    readJsonLdString(articleLd, "datePublished")
  );
  const canonicalUrl = page.canonicalUrl || page.url;

  return compact({
    title: firstNonEmpty(page.title, readJsonLdString(articleLd, "headline")),
    author,
    published_date: normalizeDate(publishedDate),
    summary: firstNonEmpty(page.description, readJsonLdString(articleLd, "description"), summarizeText(page.text)),
    canonical_url: canonicalUrl,
    site_name: metaValue(page.meta, "og:site_name"),
    word_count: countWords(page.text),
  });
}

function extractProduct(page: PageData): Record<string, unknown> {
  const productLd = findJsonLd(page.jsonLd, ["Product", "Offer", "AggregateOffer"]);
  const offers = readJsonLdObject(productLd, "offers");
  const price = firstNonEmpty(
    readJsonLdString(productLd, "price"),
    readJsonLdString(offers, "price"),
    metaValue(page.meta, "product:price:amount")
  );
  const currency = firstNonEmpty(
    readJsonLdString(productLd, "priceCurrency"),
    readJsonLdString(offers, "priceCurrency"),
    metaValue(page.meta, "product:price:currency")
  );

  return compact({
    product_name: firstNonEmpty(page.title, readJsonLdString(productLd, "name")),
    price: normalizePrice(price),
    currency: currency ? String(currency).toUpperCase() : undefined,
    availability: normalizeAvailability(
      firstNonEmpty(readJsonLdString(offers, "availability"), metaValue(page.meta, "product:availability"))
    ),
    description: firstNonEmpty(page.description, readJsonLdString(productLd, "description"), summarizeText(page.text)),
    brand: readBrand(productLd),
    category: readJsonLdString(productLd, "category"),
    rating: readAggregateRating(productLd),
    canonical_url: page.canonicalUrl || page.url,
  });
}

function extractCompany(page: PageData): Record<string, unknown> {
  const orgLd = findJsonLd(page.jsonLd, ["Organization", "Corporation", "LocalBusiness", "Store"]);
  const sameAs = readJsonLdArray(orgLd, "sameAs").filter((value) => typeof value === "string") as string[];
  const linkedinUrl = sameAs.find((value) => /linkedin\.com/i.test(value)) || findLinkedInUrl(page.links);
  const companyName = firstNonEmpty(
    readJsonLdString(orgLd, "name"),
    page.title,
    guessCompanyName(page)
  );
  const domain = page.host.replace(/^www\./i, "");
  const hq = readAddress(orgLd, page);
  const employees = normalizeEmployeeRange(readJsonLdString(orgLd, "employees"), page.text);
  const revenue = normalizeRevenueRange(readJsonLdString(orgLd, "revenue"), page.text);

  return compact({
    company_name: companyName,
    domain,
    industry: firstNonEmpty(
      readJsonLdString(orgLd, "industry"),
      metaValue(page.meta, "og:article:section"),
      guessIndustry(page)
    ),
    employee_range: employees,
    revenue_range: revenue,
    hq_city: hq.city,
    hq_country: hq.country,
    linkedin_url: linkedinUrl,
    founded_year: normalizeFoundedYear(readJsonLdString(orgLd, "foundingDate"), page.text),
    canonical_url: page.canonicalUrl || page.url,
  });
}

function extractDocs(page: PageData): Record<string, unknown> {
  const softwareLd = findJsonLd(page.jsonLd, ["TechArticle", "SoftwareApplication", "WebPage", "Article"]);
  const sections = extractHeadingSummary(page);
  return compact({
    doc_title: firstNonEmpty(page.title, readJsonLdString(softwareLd, "name")),
    section_count: sections.length,
    summary: firstNonEmpty(page.description, summarizeText(page.text)),
    canonical_url: page.canonicalUrl || page.url,
    product_name: readJsonLdString(softwareLd, "softwareVersion") || readJsonLdString(softwareLd, "name"),
    version: metaValue(page.meta, "docsearch:version") || metaValue(page.meta, "version"),
    sections,
  });
}

function buildConfidence(
  preset: Preset,
  data: Record<string, unknown>,
  page: PageData,
  sourceCoverage: number
): number {
  const fieldPresence = sourceCoverage;
  const sourceSignal = sourceSignalScore(page);
  const presetBonus = preset === "company_directory" ? 0.08 : preset === "article" ? 0.06 : 0.04;
  const textQuality = page.text.length > 1000 ? 0.05 : page.text.length > 250 ? 0.03 : 0;
  const filledFields = Object.values(data).filter(isMeaningful).length;
  const breadthBonus = Math.min(filledFields / 10, 0.1);
  return round(clamp(fieldPresence * 0.45 + sourceSignal * 0.35 + presetBonus + textQuality + breadthBonus, 0, 1), 2);
}

function buildFieldConfidence(preset: Preset, data: Record<string, unknown>, page: PageData): Record<string, number> {
  const confidence: Record<string, number> = {};
  for (const field of PRESET_FIELDS[preset]) {
    const value = data[field];
    confidence[field] = isMeaningful(value) ? fieldBaseConfidence(field, page) : 0;
  }
  return confidence;
}

function fieldBaseConfidence(field: string, page: PageData): number {
  const fromJsonLd = page.jsonLd.some((item) => Object.prototype.hasOwnProperty.call(item, field));
  if (fromJsonLd) {
    return 0.95;
  }

  const metaHit =
    field === "title"
      ? Boolean(page.title)
      : field === "summary"
        ? Boolean(page.description)
        : field === "canonical_url"
          ? Boolean(page.canonicalUrl)
          : false;

  return metaHit ? 0.8 : 0.65;
}

function buildWarnings(preset: Preset, data: Record<string, unknown>, page: PageData, locale?: string): string[] {
  const warnings: string[] = [];

  if (!page.canonicalUrl) {
    warnings.push("Canonical URL not found; using the input URL.");
  }
  if (preset === "company_directory" && !data.linkedin_url) {
    warnings.push("LinkedIn URL not found on page or structured data.");
  }
  if (preset === "company_directory" && !data.founded_year) {
    warnings.push("Founded year not detected.");
  }
  if (preset === "product_page" && !data.price) {
    warnings.push("Price not detected.");
  }
  if (preset === "article" && !data.author) {
    warnings.push("Author not detected.");
  }
  if (locale) {
    warnings.push(`Locale hint applied: ${locale}`);
  }

  return warnings;
}

async function fetchPage(url: string): Promise<PageData> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  try {
    let response: Response;
    try {
      response = await fetch(url, {
        redirect: "follow",
        signal: controller.signal,
        headers: {
          "user-agent": "Mozilla/5.0 (compatible; WebsiteToJson/1.0)",
          accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
      });
    } catch (error) {
      const cause =
        typeof error === "object" && error && "cause" in error
          ? String((error as { cause?: unknown }).cause)
          : "no-cause";
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to fetch page: ${message}; cause=${cause}`);
    }

    if (!response.ok) {
      throw new Error(`Failed to fetch page: ${response.status} ${response.statusText}`);
    }

    const contentType = response.headers.get("content-type") || "";
    if (!/html|xml/i.test(contentType)) {
      throw new Error(`Unsupported content type: ${contentType || "unknown"}`);
    }

    const html = await response.text();
    const resolvedUrl = response.url || url;
    const meta = extractMetaTags(html);
    const canonicalUrl = resolveCanonicalUrl(html, resolvedUrl);
    const jsonLd = extractJsonLd(html);
    const title = firstNonEmpty(metaValue(meta, "og:title"), extractTitle(html), extractHeading(html, "h1"));
    const description = firstNonEmpty(
      metaValue(meta, "description"),
      metaValue(meta, "og:description"),
      extractMetaName(html, "description")
    );

    return {
      url: resolvedUrl,
      canonicalUrl,
      host: new URL(resolvedUrl).host,
      title: title || "",
      description: description || "",
      html,
      text: extractVisibleText(html),
      links: extractLinks(html, resolvedUrl),
      meta,
      jsonLd,
    };
  } finally {
    clearTimeout(timeout);
  }
}

export function validateInput(input: unknown): SkillInput {
  if (!input || typeof input !== "object") {
    throw new Error("Request body must be a JSON object");
  }

  const body = input as Partial<SkillInput>;

  if (!body.url || typeof body.url !== "string") {
    throw new Error("url is required");
  }

  if (!isPreset(body.preset)) {
    throw new Error("preset must be one of article, product_page, company_directory, docs_page");
  }

  const parsed = new URL(body.url);
  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error("url must be http or https");
  }

  return {
    url: parsed.toString(),
    preset: body.preset,
    locale: body.locale,
    include_sources: body.include_sources,
  };
}

function looksLikeRequest(value: unknown): value is Request {
  return typeof value === "object" && value !== null && "json" in value && typeof (value as Request).json === "function";
}

export function successResponse(result: SkillResult): Response {
  return new Response(JSON.stringify(result, null, 2), {
    status: 200,
    headers: {
      "content-type": "application/json; charset=utf-8",
    },
  });
}

export function errorResponse(error: unknown): Response {
  const message = error instanceof Error ? error.message : "Unknown error";
  const status = message === "Unauthorized" ? 401 : message.includes("required") || message.includes("must") ? 400 : 500;
  return new Response(
    JSON.stringify(
      {
        error: message,
      },
      null,
      2
    ),
    {
      status,
      headers: {
        "content-type": "application/json; charset=utf-8",
      },
    }
  );
}

function enforceAuth(request: Request): void {
  const secret = process.env.CLAW0X_API_KEY?.trim() || process.env.SKILL_SHARED_SECRET?.trim();
  if (!secret) {
    return;
  }

  const authHeader = request.headers.get("authorization") || request.headers.get("x-skill-secret") || "";
  const token = extractBearerToken(authHeader) || authHeader.trim();
  if (!token || token !== secret) {
    throw new Error("Unauthorized");
  }
}

function extractBearerToken(value: string): string | undefined {
  const match = value.match(/^Bearer\s+(.+)$/i);
  return match ? match[1].trim() : undefined;
}

function isPreset(value: unknown): value is Preset {
  return value === "article" || value === "product_page" || value === "company_directory" || value === "docs_page";
}

function extractMetaTags(html: string): Record<string, string> {
  const meta: Record<string, string> = {};
  const metaTagRegex = /<meta\b([^>]*?)>/gi;
  let match: RegExpExecArray | null;
  while ((match = metaTagRegex.exec(html))) {
    const attrs = parseAttributes(match[1]);
    const key = attrs.property || attrs.name || attrs["http-equiv"];
    const value = attrs.content;
    if (key && value) {
      meta[key.toLowerCase()] = decodeHtml(value).trim();
    }
  }
  return meta;
}

function extractJsonLd(html: string): Record<string, unknown>[] {
  const result: Record<string, unknown>[] = [];
  const scriptRegex = /<script\b[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let match: RegExpExecArray | null;
  while ((match = scriptRegex.exec(html))) {
    const raw = match[1].trim();
    if (!raw) {
      continue;
    }

    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        for (const item of parsed) {
          if (item && typeof item === "object") {
            result.push(item as Record<string, unknown>);
          }
        }
      } else if (parsed && typeof parsed === "object") {
        if ("@graph" in parsed && Array.isArray((parsed as { "@graph"?: unknown[] })["@graph"])) {
          for (const item of (parsed as { "@graph": unknown[] })["@graph"]) {
            if (item && typeof item === "object") {
              result.push(item as Record<string, unknown>);
            }
          }
        } else {
          result.push(parsed as Record<string, unknown>);
        }
      }
    } catch {
      continue;
    }
  }
  return result;
}

function extractTitle(html: string): string {
  const match = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  return match ? decodeHtml(match[1]).trim() : "";
}

function extractHeading(html: string, tag: string): string {
  const regex = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i");
  const match = html.match(regex);
  return match ? decodeHtml(stripTags(match[1])).trim() : "";
}

function extractHeadingSummary(page: PageData): string[] {
  const headings = extractHeadings(page.html);
  return headings.slice(0, 12);
}

function extractHeadings(html: string): string[] {
  const headings: string[] = [];
  const regex = /<h[1-4][^>]*>([\s\S]*?)<\/h[1-4]>/gi;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(html))) {
    const text = decodeHtml(stripTags(match[1])).trim();
    if (text) {
      headings.push(text);
    }
  }
  return headings;
}

function extractLinks(html: string, baseUrl: string): string[] {
  const links: string[] = [];
  const regex = /<a\b[^>]*href=["']([^"']+)["'][^>]*>/gi;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(html))) {
    const href = match[1].trim();
    if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("javascript:")) {
      continue;
    }
    try {
      links.push(new URL(href, baseUrl).toString());
    } catch {
      continue;
    }
  }
  return Array.from(new Set(links));
}

function extractVisibleText(html: string): string {
  const withoutScripts = html.replace(/<script[\s\S]*?<\/script>/gi, " ");
  const withoutStyles = withoutScripts.replace(/<style[\s\S]*?<\/style>/gi, " ");
  const stripped = stripTags(withoutStyles);
  return decodeHtml(stripped).replace(/\s+/g, " ").trim();
}

function resolveCanonicalUrl(html: string, fallbackUrl: string): string {
  const canonicalMatch = html.match(/<link\b[^>]*rel=["']canonical["'][^>]*href=["']([^"']+)["'][^>]*>/i);
  if (!canonicalMatch) {
    return fallbackUrl;
  }

  try {
    return new URL(decodeHtml(canonicalMatch[1]).trim(), fallbackUrl).toString();
  } catch {
    return fallbackUrl;
  }
}

function parseAttributes(input: string): Record<string, string> {
  const attrs: Record<string, string> = {};
  const attrRegex = /([a-zA-Z_:][a-zA-Z0-9_:.-]*)\s*=\s*("([^"]*)"|'([^']*)'|([^\s"'>]+))/g;
  let match: RegExpExecArray | null;
  while ((match = attrRegex.exec(input))) {
    const key = match[1].toLowerCase();
    const value = match[3] ?? match[4] ?? match[5] ?? "";
    attrs[key] = decodeHtml(value);
  }
  return attrs;
}

function metaValue(meta: Record<string, string>, key: string): string | undefined {
  return meta[key.toLowerCase()];
}

function extractMetaName(html: string, name: string): string | undefined {
  const regex = new RegExp(`<meta\\b[^>]*name=["']${escapeRegex(name)}["'][^>]*content=["']([^"']+)["'][^>]*>`, "i");
  const match = html.match(regex);
  return match ? decodeHtml(match[1]).trim() : undefined;
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function findJsonLd(items: Record<string, unknown>[], types: string[]): Record<string, unknown> | undefined {
  return items.find((item) => {
    const value = item["@type"];
    if (typeof value === "string") {
      return types.includes(value);
    }
    if (Array.isArray(value)) {
      return value.some((entry) => typeof entry === "string" && types.includes(entry));
    }
    return false;
  });
}

function readJsonLdString(node: Record<string, unknown> | undefined, key: string): string | undefined {
  if (!node) {
    return undefined;
  }
  const value = node[key];
  if (typeof value === "string") {
    return value.trim();
  }
  if (Array.isArray(value) && typeof value[0] === "string") {
    return value[0].trim();
  }
  if (value && typeof value === "object" && "name" in value && typeof (value as { name?: unknown }).name === "string") {
    return String((value as { name: string }).name).trim();
  }
  return undefined;
}

function readJsonLdArray(node: Record<string, unknown> | undefined, key: string): unknown[] {
  if (!node) {
    return [];
  }
  const value = node[key];
  if (Array.isArray(value)) {
    return value;
  }
  if (value === undefined || value === null) {
    return [];
  }
  return [value];
}

function readJsonLdObject(node: Record<string, unknown> | undefined, key: string): Record<string, unknown> | undefined {
  if (!node) {
    return undefined;
  }
  const value = node[key];
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : undefined;
}

function readAuthor(node: Record<string, unknown> | undefined, page: PageData): string | undefined {
  const author = readJsonLdString(node, "author");
  if (author) {
    return author;
  }

  const metaAuthor = metaValue(page.meta, "author");
  if (metaAuthor) {
    return metaAuthor;
  }

  const match = page.html.match(/<meta\b[^>]*name=["']author["'][^>]*content=["']([^"']+)["'][^>]*>/i);
  return match ? decodeHtml(match[1]).trim() : undefined;
}

function readBrand(node: Record<string, unknown> | undefined): string | undefined {
  const brand = readJsonLdObject(node, "brand");
  if (brand) {
    return readJsonLdString(brand, "name");
  }
  return readJsonLdString(node, "brand");
}

function readAggregateRating(node: Record<string, unknown> | undefined): number | undefined {
  const rating = readJsonLdObject(node, "aggregateRating");
  const value = rating ? rating["ratingValue"] : undefined;
  const numeric = toNumber(value);
  return numeric !== null ? round(numeric, 2) : undefined;
}

function readAddress(node: Record<string, unknown> | undefined, page: PageData): { city?: string; country?: string } {
  const address = readJsonLdObject(node, "address");
  const city = firstNonEmpty(
    address ? readJsonLdString(address, "addressLocality") : undefined,
    findByLabel(page.text, ["hq", "headquarters", "city"])
  );
  const countryRaw = firstNonEmpty(
    address ? readJsonLdString(address, "addressCountry") : undefined,
    findByLabel(page.text, ["country"])
  );
  return {
    city: city ? cleanText(city) : undefined,
    country: countryRaw ? normalizeCountry(countryRaw) : undefined,
  };
}

function guessCompanyName(page: PageData): string | undefined {
  const title = page.title.trim();
  if (!title) {
    return undefined;
  }
  const parts = title.split(/[-–•·:]/).map((part) => part.trim()).filter(Boolean);
  return parts[0] || title;
}

function guessIndustry(page: PageData): string | undefined {
  const text = page.text.toLowerCase();
  const candidates: Array<[RegExp, string]> = [
    [/saas|software as a service|platform|api|developer tool/, "Software"],
    [/fintech|payments|banking|lending|wallet/, "Financial Services"],
    [/health|medical|clinic|pharma/, "Healthcare"],
    [/marketplace|ecommerce|e-commerce|retail/, "E-commerce"],
    [/security|cybersecurity|infosec/, "Security"],
    [/ai|machine learning|llm|generative/, "Artificial Intelligence"],
  ];
  for (const [pattern, label] of candidates) {
    if (pattern.test(text)) {
      return label;
    }
  }
  return undefined;
}

function normalizeEmployeeRange(value: string | undefined, text: string): string | undefined {
  const source = firstNonEmpty(value, findByLabel(text, ["employees", "team size", "headcount"]));
  if (!source) {
    return undefined;
  }
  const raw = source.toLowerCase().replace(/[,\s]/g, "");
  const numberMatch = raw.match(/(\d{1,6})/);
  if (numberMatch) {
    const count = Number(numberMatch[1]);
    for (const bucket of EMPLOYEE_RANGE_BUCKETS) {
      if (count <= bucket.max) {
        return bucket.label;
      }
    }
  }

  return cleanRangeLabel(source);
}

function normalizeRevenueRange(value: string | undefined, text: string): string | undefined {
  const source = firstNonEmpty(value, findByLabel(text, ["revenue", "annual revenue", "turnover"]));
  if (!source) {
    return undefined;
  }
  const numeric = parseMoneyLike(source);
  if (numeric === null) {
    return cleanRangeLabel(source);
  }
  for (const bucket of REVENUE_BUCKETS) {
    if (numeric <= bucket.max) {
      return bucket.label;
    }
  }
  return undefined;
}

function normalizeFoundedYear(value: string | undefined, text: string): number | undefined {
  const source = firstNonEmpty(value, findByLabel(text, ["founded", "established", "since"]));
  if (!source) {
    return undefined;
  }
  const match = source.match(/(19\d{2}|20\d{2})/);
  return match ? Number(match[1]) : undefined;
}

function normalizeAvailability(value: string | undefined): string | undefined {
  if (!value) {
    return undefined;
  }
  const lower = value.toLowerCase();
  if (lower.includes("instock")) {
    return "in_stock";
  }
  if (lower.includes("outofstock")) {
    return "out_of_stock";
  }
  if (lower.includes("preorder")) {
    return "preorder";
  }
  return cleanText(value);
}

function normalizePrice(value: string | undefined): number | undefined {
  if (!value) {
    return undefined;
  }
  const numeric = parseMoneyLike(value);
  return numeric === null ? undefined : round(numeric, 2);
}

function normalizeDate(value: string | undefined): string | undefined {
  if (!value) {
    return undefined;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    const match = value.match(/(19\d{2}|20\d{2})-(\d{2})-(\d{2})/);
    return match ? `${match[1]}-${match[2]}-${match[3]}` : undefined;
  }
  return date.toISOString().slice(0, 10);
}

function normalizeCountry(value: string): string {
  const key = value.toLowerCase().replace(/[^a-z.]/g, "");
  return COUNTRY_ALIASES[key] || value.replace(/\s+/g, " ").trim();
}

function cleanText(value: string): string {
  return decodeHtml(value).replace(/\s+/g, " ").trim();
}

function cleanRangeLabel(value: string): string {
  return cleanText(value).replace(/\s*-\s*/g, "-");
}

function summarizeText(text: string): string {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (cleaned.length <= 280) {
    return cleaned;
  }
  return `${cleaned.slice(0, 277).trimEnd()}...`;
}

function countWords(text: string): number {
  const words = text.trim().split(/\s+/).filter(Boolean);
  return words.length;
}

function firstNonEmpty(...values: Array<string | undefined | null>): string | undefined {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return undefined;
}

function isMeaningful(value: unknown): boolean {
  if (value === undefined || value === null) {
    return false;
  }
  if (typeof value === "string") {
    return value.trim().length > 0;
  }
  if (typeof value === "number") {
    return Number.isFinite(value);
  }
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  if (typeof value === "object") {
    return Object.keys(value as object).length > 0;
  }
  return true;
}

function compact<T extends Record<string, unknown>>(obj: T): T {
  const out = {} as T;
  for (const [key, value] of Object.entries(obj)) {
    if (isMeaningful(value)) {
      out[key as keyof T] = value as T[keyof T];
    }
  }
  return out;
}

function sourceSignalScore(page: PageData): number {
  let score = 0.45;
  if (page.jsonLd.length > 0) {
    score += 0.2;
  }
  if (page.canonicalUrl && page.canonicalUrl !== page.url) {
    score += 0.1;
  }
  if (page.description) {
    score += 0.08;
  }
  if (page.links.length > 5) {
    score += 0.05;
  }
  if (page.text.length > 1000) {
    score += 0.05;
  }
  return clamp(score, 0, 1);
}

function findLinkedInUrl(links: string[]): string | undefined {
  return links.find((link) => /linkedin\.com\/company\//i.test(link));
}

function findByLabel(text: string, labels: string[]): string | undefined {
  for (const label of labels) {
    const regex = new RegExp(`${escapeRegex(label)}\\s*[:\\-–]?\\s*([^\\n\\r\\|]{2,80})`, "i");
    const match = text.match(regex);
    if (match) {
      return cleanText(match[1]);
    }
  }
  return undefined;
}

function parseMoneyLike(value: string): number | null {
  const normalized = value.replace(/,/g, "").replace(/[^\d.-]/g, "");
  if (!normalized) {
    return null;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function toNumber(value: unknown): number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function round(value: number, digits: number): number {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function decodeHtml(value: string): string {
  return value
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ")
    .replace(/&#x2F;/g, "/")
    .replace(/&#(\d+);/g, (_, n: string) => String.fromCharCode(Number(n)))
    .replace(/&#x([0-9a-fA-F]+);/g, (_, n: string) => String.fromCharCode(Number.parseInt(n, 16)));
}

function stripTags(value: string): string {
  return value.replace(/<[^>]+>/g, " ");
}
