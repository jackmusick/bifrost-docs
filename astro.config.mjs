// @ts-check
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

// https://astro.build/config
export default defineConfig({
    integrations: [
        starlight({
            title: "Bifrost Docs",
            description:
                "Documentation for Bifrost - Open-source workflow automation for MSPs",
            logo: {
                src: "./src/assets/logo-square.svg",
            },
            favicon: "/src/assets/logo-square.svg",
            social: [
                {
                    icon: "github",
                    label: "GitHub API",
                    href: "https://github.com/jackmusick/bifrost-api",
                },
                {
                    icon: "github",
                    label: "GitHub Client",
                    href: "https://github.com/jackmusick/bifrost-client",
                },
            ],
            customCss: ["./src/styles/custom.css"],
            expressiveCode: {
                themes: ["dark-plus"],
            },
            sidebar: [
                {
                    label: "Getting Started",
                    items: [
                        { label: "Quick Start", slug: "tutorials/quickstart" },
                        {
                            label: "Build Your First Workflow",
                            slug: "tutorials/first-workflow",
                        },
                        {
                            label: "Create Dynamic Forms",
                            slug: "tutorials/creating-forms",
                        },
                        {
                            label: "OAuth Integration",
                            slug: "tutorials/oauth-integration",
                        },
                    ],
                },
                {
                    label: "Core Concepts",
                    items: [
                        {
                            label: "Platform Overview",
                            slug: "concepts/platform-overview",
                        },
                        { label: "Workflows", slug: "concepts/workflows" },
                        { label: "Forms", slug: "concepts/forms" },
                        {
                            label: "Discovery System",
                            slug: "concepts/discovery-system",
                        },
                        { label: "Permissions", slug: "concepts/permissions" },
                        { label: "Scopes", slug: "concepts/scopes" },
                    ],
                },
                {
                    label: "How-To Guides",
                    collapsed: true,
                    items: [
                        {
                            label: "Workflows",
                            collapsed: true,
                            items: [
                                {
                                    label: "Writing Workflows",
                                    slug: "guides/workflows/writing-workflows",
                                },
                                {
                                    label: "Using Decorators",
                                    slug: "guides/workflows/using-decorators",
                                },
                                {
                                    label: "Error Handling",
                                    slug: "guides/workflows/error-handling",
                                },
                            ],
                        },
                        {
                            label: "Forms",
                            collapsed: true,
                            items: [
                                {
                                    label: "Creating Forms",
                                    slug: "guides/forms/creating-forms",
                                },
                                {
                                    label: "Data Providers",
                                    slug: "guides/forms/data-providers",
                                },
                                {
                                    label: "Visibility Rules",
                                    slug: "guides/forms/visibility-rules",
                                },
                                {
                                    label: "HTML Content",
                                    slug: "guides/forms/html-content",
                                },
                                {
                                    label: "Startup Workflows",
                                    slug: "guides/forms/startup-workflows",
                                },
                                {
                                    label: "Context Field References",
                                    slug: "guides/forms/context-field-references",
                                },
                            ],
                        },
                        {
                            label: "Integrations",
                            collapsed: true,
                            items: [
                                {
                                    label: "OAuth Setup",
                                    slug: "guides/integrations/oauth-setup",
                                },
                                {
                                    label: "Secrets Management",
                                    slug: "guides/integrations/secrets-management",
                                },
                                {
                                    label: "Microsoft Graph",
                                    slug: "guides/integrations/microsoft-graph",
                                },
                                {
                                    label: "Custom APIs",
                                    slug: "guides/integrations/custom-apis",
                                },
                            ],
                        },
                        {
                            label: "Local Development",
                            collapsed: true,
                            items: [
                                {
                                    label: "Setup",
                                    slug: "guides/local-dev/setup",
                                },
                                {
                                    label: "Testing",
                                    slug: "guides/local-dev/testing",
                                },
                                {
                                    label: "Debugging",
                                    slug: "guides/local-dev/debugging",
                                },
                            ],
                        },
                        {
                            label: "Deployment",
                            collapsed: true,
                            items: [
                                {
                                    label: "Azure Setup",
                                    slug: "guides/deployment/azure-setup",
                                },
                                {
                                    label: "GitHub Actions",
                                    slug: "guides/deployment/github-actions",
                                }
                            ],
                        },
                        {
                            label: "User Interface",
                            collapsed: true,
                            items: [
                                {
                                    label: "Keyboard Shortcuts",
                                    slug: "guides/ui/keyboard-shortcuts",
                                },
                            ],
                        },
                    ],
                },
                {
                    label: "SDK Reference",
                    collapsed: true,
                    items: [
                        {
                            label: "AI Coding Guide",
                            slug: "reference/sdk/claude",
                        },
                        {
                            label: "Context API",
                            slug: "reference/sdk/context-api",
                        },
                        {
                            label: "Decorators",
                            slug: "reference/sdk/decorators",
                        },
                        {
                            label: "Bifrost Module",
                            slug: "reference/sdk/bifrost-module",
                        },
                        {
                            label: "Forms",
                            collapsed: true,
                            items: [
                                {
                                    label: "Field Types",
                                    slug: "reference/forms/field-types",
                                },
                                {
                                    label: "Context Object",
                                    slug: "reference/forms/context-object",
                                },
                                {
                                    label: "Validation Rules",
                                    slug: "reference/forms/validation-rules",
                                },
                            ],
                        },
                        {
                            label: "Architecture",
                            collapsed: true,
                            items: [
                                {
                                    label: "Overview",
                                    slug: "reference/architecture/overview",
                                },
                                {
                                    label: "Multi-Tenancy",
                                    slug: "reference/architecture/multi-tenancy",
                                },
                                {
                                    label: "Security",
                                    slug: "reference/architecture/security",
                                },
                            ],
                        },
                    ],
                },
                {
                    label: "Troubleshooting",
                    collapsed: true,
                    items: [
                        {
                            label: "Azure Functions",
                            slug: "troubleshooting/azure-functions",
                        },
                        { label: "OAuth", slug: "troubleshooting/oauth" },
                        {
                            label: "Workflow Engine",
                            slug: "troubleshooting/workflow-engine",
                        },
                        { label: "Forms", slug: "troubleshooting/forms" },
                    ],
                },
            ],
            components: {
                // Override default components if needed
            },
        }),
    ],
});
