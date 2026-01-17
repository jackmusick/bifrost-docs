# High Priority

-   [x] All entities -- configurations, locations, passwords, documents and custom assets should edit in-line rather than a modal dialog.
-   [x] The Configurations section should be a page called Configurations, not a page per configuration type. Configuration Type would just be a column.

# Low Priority

-   [x] Ability to organize the order and Section Custom Assets appear in from the Settings menu.

# Polish

-   [ ] Tables in views like the documents, configurations, etc. -- anything with a table -- should show the minimum amount of space they need, but no more than the remaining page height. It should scroll within itself after that.
-   [ ] Sidebar with folders in documents view should now expand infinitely. Same as tables above.
-   [ ] This is noticeable so far mostly in the edit view on things like password, configurations and custom assets. When we have a grey card, input is hard to distinquish because it has the same grey background. I don't think this is a problem by default in shadcn and we might've fixed it in ../bifrost-api. Open to recommendations.
-   [ ] When a notes field is a selected column, we see the plain HTML in the table, not formatted at all. What would you recommend for this? I'm not sure we want to keep formatting, because it could really mess up the table. Possibly not allow rich text fields to be selected?
-   [ ] Standardize on a better placement for the "Show Disabled" button on all pages. Currently, it's taking up a dedicated row. My vote is it goes in the Action Bar with "Add Site Summary", far left.
-   [ ] Custom Assets are missing a Show Disabled option.
-   [ ] For Custom Assets, allow selecting a field to replace "Name". Not sure the best strategy around this, but the problem is when importing with our itglue importer, some custom assets use "Title" or something similar, which is really their "display field" is how IT Glue calls it. For us that means we end up with a name and a title, and the name is something like "Asset 123456".
-   [ ] Need to be able to be able to turn off indexing in the Settings. Useful during migrations.
-   [ ] Need to gracefully disable the AI button in search if AI isn't configured, also skip sending save operations off to indexing.
