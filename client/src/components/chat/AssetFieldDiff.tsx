import React from 'react';

interface AssetFieldDiffProps {
  fieldUpdates: Record<string, string>;
  summary: string;
  currentFields?: Record<string, string>;
}

export const AssetFieldDiff: React.FC<AssetFieldDiffProps> = ({
  fieldUpdates,
  summary,
  currentFields = {},
}) => {
  return (
    <div className="asset-field-diff border rounded-lg p-4 space-y-4 bg-muted/30">
      <div className="preview-summary">
        <strong className="text-sm font-semibold">Changes Summary:</strong>
        <p className="text-sm text-muted-foreground mt-1">{summary}</p>
      </div>

      <div className="field-changes">
        <strong className="text-sm font-semibold">Field Changes:</strong>
        <div className="mt-2 overflow-x-auto">
          <table className="field-diff-table w-full border-collapse border border-border rounded-md overflow-hidden">
            <thead>
              <tr className="bg-muted">
                <th className="border border-border px-3 py-2 text-left text-sm font-semibold">
                  Field
                </th>
                <th className="border border-border px-3 py-2 text-left text-sm font-semibold">
                  Old → New
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(fieldUpdates).map(([field, newValue]) => (
                <tr key={field} className="hover:bg-muted/50">
                  <td className="border border-border px-3 py-2 text-sm font-medium">
                    {field}
                  </td>
                  <td className="border border-border px-3 py-2 text-sm">
                    {currentFields[field] ? (
                      <>
                        <span className="old-value text-muted-foreground line-through">
                          {currentFields[field]}
                        </span>
                        {' → '}
                        <span className="new-value text-foreground font-medium">
                          {newValue}
                        </span>
                      </>
                    ) : (
                      <span className="new-value text-foreground font-medium">
                        {newValue}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
