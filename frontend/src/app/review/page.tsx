"use client";

import { Page } from "@/components/shell";
import { PageHeader } from "@/components/ui";

/** V3-7, Review: the combined books as a workbook the controller edits, with the Reviewer asking why (D19).
 * A placeholder for now: the shell and the title. The editing still lives on the Case until the Review task moves it. */
export default function ReviewScreen() {
  return (
    <Page>
      <PageHeader title="Review" />
    </Page>
  );
}
