import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Link2, Plus, X, Loader2, LinkIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  useRelationships,
  useDeleteRelationship,
  groupRelationshipsByType,
  type ResolvedRelationship,
} from "@/hooks/useRelationships";
import {
  getEntityIcon,
  getEntityLabel,
  getEntityRoute,
  type EntityType,
} from "@/lib/entity-icons";
import { AddRelationshipDialog } from "./AddRelationshipDialog";
import { toast } from "sonner";

interface RelatedItemsSidebarProps {
  orgId: string;
  entityType: EntityType;
  entityId: string;
}

export function RelatedItemsSidebar({
  orgId,
  entityType,
  entityId,
}: RelatedItemsSidebarProps) {
  const navigate = useNavigate();
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);

  const { data, isLoading, error } = useRelationships(orgId, entityType, entityId);
  const deleteRelationship = useDeleteRelationship(orgId);

  const relationships = data?.relationships ?? [];
  const groupedRelationships = groupRelationshipsByType(relationships);
  const entityTypes = Object.keys(groupedRelationships) as EntityType[];

  const handleNavigate = (rel: ResolvedRelationship) => {
    const route = getEntityRoute(rel.entity.entity_type);
    let path: string;

    if (rel.entity.entity_type === "custom_asset" && rel.entity.asset_type_id) {
      path = `/org/${orgId}/${route}/${rel.entity.asset_type_id}/${rel.entity.id}`;
    } else {
      path = `/org/${orgId}/${route}/${rel.entity.id}`;
    }

    navigate(path);
  };

  const handleRemoveRelationship = async (
    rel: ResolvedRelationship,
    e: React.MouseEvent
  ) => {
    e.stopPropagation();
    try {
      await deleteRelationship.mutateAsync(rel.relationship.id);
      toast.success("Relationship removed");
    } catch {
      toast.error("Failed to remove relationship");
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Link2 className="h-4 w-4" />
            Related Items
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Link2 className="h-4 w-4" />
            Related Items
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">Failed to load relationships</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Link2 className="h-4 w-4" />
              Related Items
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={() => setIsAddDialogOpen(true)}
            >
              <Plus className="h-4 w-4" />
              <span className="sr-only">Add relationship</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {relationships.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-6 text-center">
              <LinkIcon className="h-8 w-8 text-muted-foreground/50 mb-2" />
              <p className="text-sm text-muted-foreground mb-3">
                No related items yet
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAddDialogOpen(true)}
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Relationship
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {entityTypes.map((type) => {
                const Icon = getEntityIcon(type);
                const label = getEntityLabel(type);
                const rels = groupedRelationships[type];

                return (
                  <div key={type}>
                    <div className="flex items-center gap-2 mb-2">
                      <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        {label}s
                      </span>
                      <Badge variant="secondary" className="ml-auto text-xs">
                        {rels.length}
                      </Badge>
                    </div>
                    <div className="space-y-1">
                      {rels.map((rel) => (
                        <div
                          key={rel.relationship.id}
                          className="group flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-muted cursor-pointer transition-colors"
                          onClick={() => handleNavigate(rel)}
                        >
                          <span className="text-sm truncate flex-1">
                            {rel.entity.name}
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={(e) => handleRemoveRelationship(rel, e)}
                            disabled={deleteRelationship.isPending}
                          >
                            {deleteRelationship.isPending ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <X className="h-3 w-3" />
                            )}
                            <span className="sr-only">Remove relationship</span>
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}

              <div className="pt-2 border-t">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-muted-foreground"
                  onClick={() => setIsAddDialogOpen(true)}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add relationship
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <AddRelationshipDialog
        open={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
        orgId={orgId}
        sourceEntityType={entityType}
        sourceEntityId={entityId}
      />
    </>
  );
}
