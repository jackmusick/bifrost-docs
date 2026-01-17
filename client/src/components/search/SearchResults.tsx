import { useNavigate } from "react-router-dom";
import { Building2 } from "lucide-react";
import { CommandGroup, CommandItem } from "@/components/ui/command";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { SearchResult, GroupedSearchResults } from "@/hooks/useSearch";
import {
  getEntityIcon,
  getEntityLabel,
  getEntityRoute,
  type EntityType,
} from "@/lib/entity-icons";
import { HighlightedText } from "./HighlightedText";

interface SearchResultsProps {
  groupedResults: GroupedSearchResults;
  onSelect: () => void;
  onHover?: (result: SearchResult) => void;
  highlightQuery?: string;
}

export function SearchResults({
  groupedResults,
  onSelect,
  onHover,
  highlightQuery,
}: SearchResultsProps) {
  const navigate = useNavigate();

  const handleSelect = (result: SearchResult) => {
    const route = getEntityRoute(result.entity_type);
    let path: string;

    if (result.entity_type === "custom_asset" && result.asset_type_id) {
      path = `/org/${result.organization_id}/${route}/${result.asset_type_id}/${result.entity_id}`;
    } else {
      path = `/org/${result.organization_id}/${route}/${result.entity_id}`;
    }

    navigate(path);
    onSelect();
  };

  const organizationNames = Object.keys(groupedResults);

  if (organizationNames.length === 0) {
    return null;
  }

  return (
    <>
      {organizationNames.map((orgName) => {
        const orgData = groupedResults[orgName];
        const entityTypes = Object.keys(orgData.byType) as EntityType[];

        return (
          <CommandGroup
            key={orgData.organizationId}
            heading={
              <div className="flex items-center gap-2 py-1">
                <Building2 className="h-3.5 w-3.5" />
                <span>{orgName}</span>
              </div>
            }
          >
            {entityTypes.map((entityType) => {
              const Icon = getEntityIcon(entityType);
              const label = getEntityLabel(entityType);
              const results = orgData.byType[entityType];

              return results.map((result) => (
                <CommandItem
                  key={`${result.entity_type}-${result.entity_id}`}
                  value={`${result.name} ${result.snippet} ${orgName}`}
                  onSelect={() => handleSelect(result)}
                  onMouseEnter={() => onHover?.(result)}
                  onFocus={() => onHover?.(result)}
                  className={cn(
                    "flex items-start gap-3 py-3",
                    !result.is_enabled && "opacity-60"
                  )}
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">
                        <HighlightedText
                          text={result.name}
                          highlight={highlightQuery}
                        />
                      </span>
                      <Badge variant="secondary" className="text-xs shrink-0">
                        {label}
                      </Badge>
                      {!result.is_enabled && (
                        <Badge variant="outline" className="text-xs shrink-0 text-muted-foreground">
                          Disabled
                        </Badge>
                      )}
                    </div>
                    {result.snippet && (
                      <p className="text-sm text-muted-foreground truncate mt-0.5">
                        <HighlightedText
                          text={result.snippet}
                          highlight={highlightQuery}
                        />
                      </p>
                    )}
                  </div>
                </CommandItem>
              ));
            })}
          </CommandGroup>
        );
      })}
    </>
  );
}

