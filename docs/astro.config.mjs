// @ts-check
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import sitemap from "@astrojs/sitemap";

export default defineConfig({
  site: "https://nspc911.github.io/rovr",
  integrations: [
    starlight({
      title: "rovr docs",
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/NSPC911/rovr",
        },
        /* to-do: create a link that always leads to discord, instead of hardcoding it here */
        {
          icon: "discord",
          label: "Discord",
          href: "https://discord.com/invite/smDsD9Pmbz",
        },
      ],
      customCss: ["./src/styles/custom.css"],
      sidebar: [
        { label: "overview", slug: "overview" },
        {
          label: "get Started",
          items: [
            { label: "installation", slug: "get-started/installation" },
            { label: "tutorial", slug: "get-started/tutorial" },
          ],
        },
        {
          label: "guides",
          items: [
            { label: "user interface", slug: "guides/user-interface" },
            { label: "file operations", slug: "guides/file-operations" },
          ],
        },
        {
          label: "configuration",
          items: [
            { label: "configuration", slug: "configuration/configuration" },
            { label: "themeing", slug: "configuration/themeing" },
          ],
        },
        {
          label: "features",
          items: [
            { label: "previewing files", slug: "features/previewing-files" },
            { label: "image previews", slug: "features/image-previews" },
            { label: "search", slug: "features/search" },
            { label: "plugins", slug: "features/plugins" },
          ],
        },
        {
          label: "contributing",
          items: [
            {
              label: "project structure",
              slug: "contributing/project-structure",
            },
          ],
        },
        {
          label: "reference",
          items: [
            { label: "keybindings", slug: "reference/keybindings" },
            { label: "config schema", slug: "reference/schema" },
          ],
        },
      ],
    }),
    sitemap(),
  ],
});
