import { useState, useCallback } from "react";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";
import { Badge } from "@/components/ui/badge";
import { useDebounce } from "@/hooks/useDebounce";
import { useSearch, groupSearchResults, type SearchResult } from "@/hooks/useSearch";
import { useCreateRelationship } from "@/hooks/useRelationships";
import { getEntityIcon, getEntityLabel, type EntityType } from "@/lib/entity-icons";
import { toast } from "sonner";

interface AddRelationshipDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orgId: string;
  sourceEntityType: EntityType;
  sourceEntityId: string;
}

export function AddRelationshipDialog({
  open,
  onOpenChange,
  orgId,
  sourceEntityType,
  sourceEntityId,
}: AddRelationshipDialogProps) {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounce(query, 300);

  const { data, isLoading, isFetching } = useSearch(debouncedQuery, { orgId });
  const createRelationship = useCreateRelationship(orgId);

  // Filter out the current entity from search results
  const filteredResults =
    data?.results?.filter(
      (r) =>
        !(r.entity_type === sourceEntityType && r.entity_id === sourceEntityId)
    ) ?? [];

  const groupedResults = groupSearchResults(filteredResults);

  const handleSelect = useCallback(
    async (result: SearchResult) => {
      try {
        await createRelationship.mutateAsync({
          source_entity_type: sourceEntityType,
          source_entity_id: sourceEntityId,
          target_entity_type: result.entity_type,
          target_entity_id: result.entity_id,
        });
        toast.success(`Linked to "${result.name}"`);
        setQuery("");
        onOpenChange(false);
      } catch {
        toast.error("Failed to create relationship");
      }
    },
    [
      createRelationship,
      sourceEntityType,
      sourceEntityId,
      onOpenChange,
    ]
  );

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setQuery("");
    }
    onOpenChange(newOpen);
  };

  const showLoading =
    isLoading || (isFetching && debouncedQuery.length >= 2);
  const showEmpty =
    debouncedQuery.length >= 2 &&
    !showLoading &&
    Object.keys(groupedResults).length === 0;
  const showResults =
    debouncedQuery.length >= 2 && Object.keys(groupedResults).length > 0;
  const showHint = debouncedQuery.length < 2;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md overflow-hidden p-0">
        <DialogHeader className="px-4 pt-4 pb-2">
          <DialogTitle>Add Related Item</DialogTitle>
          <DialogDescription>
            Search for an item to link to this {getEntityLabel(sourceEntityType).toLowerCase()}
          </DialogDescription>
        </DialogHeader>
        <Command className="border-t">
          <CommandInput
            placeholder="Search items..."
            value={query}
            onValueChange={setQuery}
          />
          <CommandList className="max-h-[300px]">
            {showHint && (
              <div className="py-6 text-center text-sm text-muted-foreground">
                Type at least 2 characters to search
              </div>
            )}

            {showLoading && (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">
                  Searching...
                </span>
              </div>
            )}

            {showEmpty && (
              <CommandEmpty>No items found</CommandEmpty>
            )}

            {showResults &&
              Object.entries(groupedResults).map(([orgName, orgData]) =>
                Object.entries(orgData.byType).map(([entityType, results]) => {
                  const Icon = getEntityIcon(entityType);
                  const label = getEntityLabel(entityType);

                  return (
                    <CommandGroup
                      key={`${orgName}-${entityType}`}
                      heading={label}
                    >
                      {results.map((result) => (
                        <CommandItem
                          key={`${result.entity_type}-${result.entity_id}`}
                          value={`${result.name} ${result.snippet}`}
                          onSelect={() => handleSelect(result)}
                          disabled={createRelationship.isPending}
                          className="flex items-start gap-3 py-2"
                        >
                          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-muted">
                            <Icon className="h-3.5 w-3.5" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium truncate">
                                {result.name}
                              </span>
                              <Badge
                                variant="secondary"
                                className="text-xs shrink-0"
                              >
                                {label}
                              </Badge>
                            </div>
                            {result.snippet && (
                              <p className="text-xs text-muted-foreground truncate mt-0.5">
                                {result.snippet}
                              </p>
                            )}
                          </div>
                          {createRelationship.isPending && (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          )}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  );
                })
              )}
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
