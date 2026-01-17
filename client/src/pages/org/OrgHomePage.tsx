import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  KeyRound,
  Server,
  MapPin,
  FileText,
  Layers,
  ArrowRight,
  Pencil,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { RecentEntityCard } from "@/components/RecentEntityCard";
import { useOrganization, useUpdateOrganization } from "@/hooks/useOrganizations";
import { usePermissions } from "@/hooks/usePermissions";
import { usePasswords } from "@/hooks/usePasswords";
import { useConfigurations } from "@/hooks/useConfigurations";
import { useLocations } from "@/hooks/useLocations";
import { useDocuments } from "@/hooks/useDocuments";

interface QuickLinkProps {
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  onClick: () => void;
}

function QuickLink({
  title,
  description,
  icon: Icon,
  onClick,
}: QuickLinkProps) {
  return (
    <Card
      className="hover:border-primary/50 transition-colors cursor-pointer group"
      onClick={onClick}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <ArrowRight className="h-5 w-5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </CardHeader>
      <CardContent>
        <CardTitle className="text-base mb-1">{title}</CardTitle>
        <CardDescription className="text-sm">{description}</CardDescription>
      </CardContent>
    </Card>
  );
}

export function OrgHomePage() {
  const { orgId } = useParams<{ orgId: string }>();
  const navigate = useNavigate();
  const { data: organization, isLoading } = useOrganization(orgId || "", {
    include: ["frequently_accessed"],
  });

  const frequentItems = organization?.frequently_accessed || [];
  const updateOrganization = useUpdateOrganization();
  const { canEdit } = usePermissions();

  // Fetch counts for stat cards (limit: 1 to minimize data transfer)
  const { data: passwordsData } = usePasswords(orgId || "", { pagination: { limit: 1, offset: 0 } });
  const { data: configurationsData } = useConfigurations(orgId || "", { pagination: { limit: 1, offset: 0 } });
  const { data: locationsData } = useLocations(orgId || "", { pagination: { limit: 1, offset: 0 } });
  const { data: documentsData } = useDocuments(orgId || "", { pagination: { limit: 1, offset: 0 } });

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editName, setEditName] = useState("");

  const handleEditOpen = () => {
    setEditName(organization?.name || "");
    setEditDialogOpen(true);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!editName.trim()) {
      toast.error("Please enter an organization name");
      return;
    }

    if (!orgId) return;

    try {
      await updateOrganization.mutateAsync({
        id: orgId,
        data: { name: editName.trim() },
      });
      toast.success("Organization updated successfully");
      setEditDialogOpen(false);
    } catch (error) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast.error(axiosError.response?.data?.detail || "Failed to update organization");
    }
  };

  const handleToggleEnabled = async (checked: boolean) => {
    if (!orgId) return;

    try {
      await updateOrganization.mutateAsync({
        id: orgId,
        data: { is_enabled: checked },
      });
      toast.success(checked ? "Organization enabled" : "Organization disabled");
    } catch (error) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast.error(axiosError.response?.data?.detail || "Failed to update organization");
    }
  };

  const quickLinks = [
    {
      title: "Passwords",
      description: "Securely store and manage credentials",
      icon: KeyRound,
      href: `/org/${orgId}/passwords`,
    },
    {
      title: "Configurations",
      description: "Document system configurations",
      icon: Server,
      href: `/org/${orgId}/configurations`,
    },
    {
      title: "Locations",
      description: "Track physical and virtual locations",
      icon: MapPin,
      href: `/org/${orgId}/locations`,
    },
    {
      title: "Documents",
      description: "Store and organize documentation",
      icon: FileText,
      href: `/org/${orgId}/documents`,
    },
    {
      title: "Custom Assets",
      description: "Create custom asset types",
      icon: Layers,
      href: `/org/${orgId}/assets`,
    },
  ];

  if (isLoading) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-[140px] w-full" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h1 className="text-3xl font-bold tracking-tight">
            {organization?.name || "Organization"}
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage your organization's documentation
          </p>
        </div>
        {canEdit && (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Switch
                checked={organization?.is_enabled ?? true}
                onCheckedChange={handleToggleEnabled}
                disabled={updateOrganization.isPending}
              />
              <span className="text-sm text-muted-foreground">
                {organization?.is_enabled ? "Enabled" : "Disabled"}
              </span>
            </div>
            <Button variant="outline" size="sm" onClick={handleEditOpen}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </Button>
          </div>
        )}
      </div>

      {/* Disabled Banner */}
      {organization && !organization.is_enabled && (
        <Alert variant="destructive">
          <AlertDescription>
            This organization has been disabled and will not appear in search or lists
          </AlertDescription>
        </Alert>
      )}

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Passwords</CardDescription>
            <CardTitle className="text-2xl">{passwordsData?.total ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Configurations</CardDescription>
            <CardTitle className="text-2xl">{configurationsData?.total ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Locations</CardDescription>
            <CardTitle className="text-2xl">{locationsData?.total ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Documents</CardDescription>
            <CardTitle className="text-2xl">{documentsData?.total ?? 0}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Frequently Accessed Section */}
      {frequentItems.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Frequently Accessed</h2>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {frequentItems.map((item) => (
              <RecentEntityCard
                key={`${item.entity_type}-${item.entity_id}`}
                entityType={item.entity_type}
                entityId={item.entity_id}
                organizationId={orgId || null}
                orgName={null}
                name={item.name}
                showOrg={false}
              />
            ))}
          </div>
        </div>
      )}

      {/* Quick Links */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Quick Links</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {quickLinks.map((link) => (
            <QuickLink
              key={link.href}
              title={link.title}
              description={link.description}
              icon={link.icon}
              href={link.href}
              onClick={() => navigate(link.href)}
            />
          ))}
        </div>
      </div>

      {/* Edit Organization Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <form onSubmit={handleEditSubmit}>
            <DialogHeader>
              <DialogTitle>Edit Organization</DialogTitle>
              <DialogDescription>
                Update your organization's name.
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <Label htmlFor="edit-org-name">Organization Name</Label>
              <Input
                id="edit-org-name"
                placeholder="Acme Corporation"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="mt-2"
                autoFocus
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={updateOrganization.isPending}>
                {updateOrganization.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Save
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
