import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Building2, Plus, Loader2, Search } from "lucide-react";
import { useDebounce } from "@/hooks/useDebounce";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useOrganizations, useCreateOrganization } from "@/hooks/useOrganizations";
import { useRecentlyAccessed } from "@/hooks/useRecentlyAccessed";
import { RecentEntityCard } from "@/components/RecentEntityCard";

interface CreateOrgDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  newOrgName: string;
  onNewOrgNameChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isPending: boolean;
}

function CreateOrgDialog({
  open,
  onOpenChange,
  newOrgName,
  onNewOrgNameChange,
  onSubmit,
  isPending,
}: CreateOrgDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Create Organization
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={onSubmit}>
          <DialogHeader>
            <DialogTitle>Create Organization</DialogTitle>
            <DialogDescription>
              Create a new organization to start documenting your IT infrastructure.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="org-name">Organization Name</Label>
            <Input
              id="org-name"
              placeholder="Acme Corporation"
              value={newOrgName}
              onChange={(e) => onNewOrgNameChange(e.target.value)}
              className="mt-2"
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Create
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function OrganizationsListPage() {
  const navigate = useNavigate();
  const [showDisabled, setShowDisabled] = useState(false);
  const { data: organizations, isLoading } = useOrganizations({ showDisabled });
  const createOrganization = useCreateOrganization();
  const { data: recentItems } = useRecentlyAccessed(6);
  const recentOrgs = recentItems?.filter((item) => item.entity_type === "organization") || [];

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newOrgName, setNewOrgName] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearch = useDebounce(searchQuery, 300);

  const filteredOrganizations = useMemo(() => {
    if (!organizations) return [];
    if (!debouncedSearch.trim()) return organizations;

    const query = debouncedSearch.toLowerCase();
    return organizations.filter((org) =>
      org.name.toLowerCase().includes(query)
    );
  }, [organizations, debouncedSearch]);

  const handleCreateOrganization = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newOrgName.trim()) {
      toast.error("Please enter an organization name");
      return;
    }

    try {
      const result = await createOrganization.mutateAsync({ name: newOrgName.trim() });
      toast.success("Organization created successfully");
      setIsCreateDialogOpen(false);
      setNewOrgName("");
      // Navigate to the new organization
      navigate(`/org/${result.data.id}`);
    } catch (error) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast.error(axiosError.response?.data?.detail || "Failed to create organization");
    }
  };

  const dialogProps: CreateOrgDialogProps = {
    open: isCreateDialogOpen,
    onOpenChange: setIsCreateDialogOpen,
    newOrgName,
    onNewOrgNameChange: setNewOrgName,
    onSubmit: handleCreateOrganization,
    isPending: createOrganization.isPending,
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Organizations</h1>
          <p className="text-muted-foreground mt-1">
            Manage your organizations and their documentation
          </p>
        </div>
        {organizations && organizations.length > 0 && (
          <CreateOrgDialog {...dialogProps} />
        )}
      </div>

      {organizations && organizations.length > 0 && (
        <div className="flex items-center gap-4">
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search organizations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={showDisabled}
              onCheckedChange={setShowDisabled}
            />
            <Label className="cursor-pointer" htmlFor="show-disabled">
              Show Disabled
            </Label>
          </div>
        </div>
      )}

      {/* Recent Organizations Section */}
      {recentOrgs.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Recent</h2>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {recentOrgs.map((item) => (
              <RecentEntityCard
                key={item.entity_id}
                entityType={item.entity_type}
                entityId={item.entity_id}
                organizationId={item.organization_id}
                orgName={item.org_name}
                name={item.name}
                showOrg={false}
              />
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          <>
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-[140px] w-full" />
            ))}
          </>
        ) : filteredOrganizations.length > 0 ? (
          filteredOrganizations.map((org) => (
            <Card
              key={org.id}
              className={`hover:border-primary/50 transition-colors cursor-pointer ${
                !org.is_enabled ? "opacity-60" : ""
              }`}
              onClick={() => navigate(`/org/${org.id}`)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Building2 className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <CardTitle className={`text-lg ${!org.is_enabled ? "line-through" : ""}`}>
                        {org.name}
                      </CardTitle>
                      {!org.is_enabled && (
                        <Badge variant="secondary" className="text-xs">
                          Disabled
                        </Badge>
                      )}
                    </div>
                    <CardDescription className="text-xs">
                      Created{" "}
                      {new Date(org.created_at).toLocaleDateString()}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Click to manage documentation
                </p>
              </CardContent>
            </Card>
          ))
        ) : organizations && organizations.length > 0 ? (
          <Card className="col-span-full">
            <CardContent className="flex flex-col items-center justify-center py-10">
              <Search className="h-12 w-12 text-muted-foreground/50 mb-4" />
              <h3 className="text-lg font-medium mb-1">No results found</h3>
              <p className="text-sm text-muted-foreground text-center">
                No organizations match "{debouncedSearch}"
              </p>
            </CardContent>
          </Card>
        ) : (
          <Card className="col-span-full">
            <CardContent className="flex flex-col items-center justify-center py-10">
              <Building2 className="h-12 w-12 text-muted-foreground/50 mb-4" />
              <h3 className="text-lg font-medium mb-1">No organizations yet</h3>
              <p className="text-sm text-muted-foreground mb-4 text-center">
                Create your first organization to start documenting
              </p>
              <CreateOrgDialog {...dialogProps} />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
