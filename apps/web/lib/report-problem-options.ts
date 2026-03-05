export const REPORT_PROBLEM_OPTIONS = [
  { value: "location", label: "Location is wrong" },
  { value: "styles", label: "Styles are wrong" },
  { value: "links", label: "Links are wrong / broken" },
  { value: "duplicate", label: "Duplicate artist" },
  { value: "images", label: "Images are wrong / unrelated" },
  { value: "name", label: "Name is wrong" },
  { value: "other", label: "Other" },
] as const;
