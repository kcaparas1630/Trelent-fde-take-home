# Trelent Forward-Deployed Engineer Take-Home
Welcome to the Trelent FDE take-home! This exercise builds directly on the technical question from your application.

### Problem recap

A customer has a messy folder of internal guides (PDFs, Word docs, etc.) and wants them turned into a clean set of HTML “guides” following a consistent template. Some new guides combine multiple old documents; others reuse sections. You have:

* The **Trelent Data Ingestion API** that converts any file to Markdown, which takes a while to run.
* The **OpenAI API** to rewrite and format content, which can be slow or occasionally fail.

Runs may process anywhere from a few to thousands of guides. This should be a **repeatable background pipeline**, not a single blocking web request, and it ultimately needs to be usable by non-technical users who don’t think in terms of “jobs” or “pipelines.”

### Your task

In this take-home, we want to see how you turn that idea into a small end-to-end prototype:

* **Next JS UI (`/web`):**
  Build a minimal Next.js app that lets someone at Trelent trigger your workflow and see what happened. It doesn't need to be beautiful; it does need to be obvious how to use it, and a great version would be one that is usable by non-technical users who don't think in terms of "jobs" or "pipelines" or "queues".

* **Backend workflow (scripts/services):**
  Implement a scrappy but real pipeline (Python is ideal, but use what you're fastest in) that *could* orchestrate ingestion, search, and LLM rewriting for a batch of guides. Focus on structure, error handling, and how you'd scale it up, even if some pieces are stubbed or mocked.

* **IMPORTANT: Replace this README with a short, clear explanation of:**

  * What you built and how to run it
  * How the pieces fit together
  * Key tradeoffs you made
  * What you'd do next with more time

**BONUS:** Make a docker compose file that can be used to run everything. If it's difficult for us to run your prototype end to end, we cannot effectively evaluate it.

You’re free to add additional projects or packages in the repo as needed—just stick to the package tools described in `/scripts/README.md` and `/web/README.md`.

### Ingestion API
Trelent's data ingestion API is a REST API with prebuilt SDKs for Python and Typescript. In the take-home portal, you will find an auth token to use the API in your testing. Set the base URL as `https://api.trelent.com`. You can read the documentation [here](https://docs.trelent.com/). We recommend using the `File` connector to upload files to the API then convert them. If you really want, you may use an external service to upload files somewhere and use our APIs `URL` connector to convert them.

Unlike the application question, we will not be providing you a search API as it requires additional infrastructure to be built.