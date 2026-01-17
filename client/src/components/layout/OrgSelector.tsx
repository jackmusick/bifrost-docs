import { useState, useEffect } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import {
    ArrowRight,
    Building2,
    Check,
    ChevronsUpDown,
    Globe,
    Loader2,
    Plus,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
    CommandSeparator,
} from "@/components/ui/command";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
    useOrganizations,
    useCreateOrganization,
} from "@/hooks/useOrganizations";
import { useOrganizationStore } from "@/stores/organization.store";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { Organization } from "@/lib/api-client";

export function OrgSelector() {
    const navigate = useNavigate();
    const location = useLocation();
    const { orgId } = useParams();
    const [showDisabled, setShowDisabled] = useState(false);
    const { data: organizations, isLoading, refetch } = useOrganizations({ showDisabled });
    const createOrganization = useCreateOrganization();
    const { currentOrg, setCurrentOrg, isValidating, setIsValidating } =
        useOrganizationStore();
    const [open, setOpen] = useState(false);
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [newOrgName, setNewOrgName] = useState("");

    // Check if we're on global view
    const isGlobalView = location.pathname.startsWith("/global");

    // Find current org from URL param or stored value
    const selectedOrg =
        organizations?.find((org) => org.id === orgId) ||
        currentOrg ||
        organizations?.[0];

    // Validate selected org after refetch
    useEffect(() => {
        if (isValidating && organizations && !isLoading) {
            // Check if current org still exists in fresh org list
            if (
                currentOrg &&
                !isGlobalView &&
                !organizations.find((org) => org.id === currentOrg.id)
            ) {
                // Selected org no longer exists, redirect to global
                toast.info(
                    "The selected organization is no longer available. Redirecting to global view.",
                    { duration: 5000 }
                );
                setCurrentOrg(null);
                navigate("/global");
            }
            setIsValidating(false);
        }
    }, [
        isValidating,
        organizations,
        isLoading,
        currentOrg,
        isGlobalView,
        setCurrentOrg,
        setIsValidating,
        navigate,
    ]);

    // Handle popover open/close
    const handleOpenChange = async (newOpen: boolean) => {
        setOpen(newOpen);

        if (newOpen) {
            // Refetch organizations when popover opens
            setIsValidating(true);
            try {
                await refetch();
            } catch (error) {
                setIsValidating(false);
                toast.error("Failed to refresh organization list");
            }
        }
    };

    const handleGlobalView = () => {
        setOpen(false);
        navigate("/global");
    };

    const handleOrgSelect = (org: Organization) => {
        // Prevent selection of disabled organizations
        if (!org.is_enabled) return;

        setCurrentOrg(org);
        setOpen(false);
        navigate(`/org/${org.id}`);
    };

    const handleCreateOrg = () => {
        setOpen(false);
        setCreateDialogOpen(true);
    };

    const handleCreateSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!newOrgName.trim()) {
            toast.error("Please enter an organization name");
            return;
        }

        try {
            const result = await createOrganization.mutateAsync({
                name: newOrgName.trim(),
            });
            toast.success("Organization created successfully");
            setCreateDialogOpen(false);
            setNewOrgName("");
            navigate(`/org/${result.data.id}`);
        } catch (error) {
            const axiosError = error as {
                response?: { data?: { detail?: string } };
            };
            toast.error(
                axiosError.response?.data?.detail ||
                    "Failed to create organization"
            );
        }
    };

    if (isLoading) {
        return <Skeleton className="h-9 w-[200px]" />;
    }

    return (
        <>
            <div className="flex items-center gap-1">
                <Popover open={open} onOpenChange={handleOpenChange}>
                    <PopoverTrigger asChild>
                        <Button
                            variant="outline"
                            role="combobox"
                            aria-expanded={open}
                            className="w-[280px] justify-between"
                        >
                            <span className="flex items-center gap-2 truncate">
                                {isGlobalView ? (
                                    <Globe className="h-4 w-4 shrink-0" />
                                ) : (
                                    <Building2 className="h-4 w-4 shrink-0" />
                                )}
                                <span className="truncate">
                                    {isGlobalView
                                        ? "Global View"
                                        : selectedOrg?.name ||
                                          "Select organization"}
                                </span>
                            </span>
                            <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[280px] p-0" align="start">
                        <Command>
                            <CommandInput
                                placeholder="Search organizations..."
                                disabled={isValidating}
                            />
                            <CommandList>
                                {isValidating ? (
                                    <div className="flex items-center justify-center py-6 text-sm text-muted-foreground">
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Refreshing...
                                    </div>
                                ) : (
                                    <>
                                        <CommandEmpty>
                                            No organization found.
                                        </CommandEmpty>
                                        <CommandGroup>
                                            <CommandItem
                                                value="global-view"
                                                onSelect={handleGlobalView}
                                                className="cursor-pointer flex items-center"
                                            >
                                                <Check
                                                    className={cn(
                                                        "mr-2 h-4 w-4 shrink-0",
                                                        isGlobalView
                                                            ? "opacity-100"
                                                            : "opacity-0"
                                                    )}
                                                />
                                                <Globe className="mr-2 h-4 w-4 shrink-0" />
                                                <span>Global</span>
                                            </CommandItem>
                                        </CommandGroup>
                                        <CommandSeparator />
                                        <CommandGroup
                                            heading={
                                                organizations && organizations.length > 0
                                                    ? `Organizations (${
                                                        organizations.filter(org => org.is_enabled).length
                                                    }${
                                                        showDisabled && organizations.filter(org => !org.is_enabled).length > 0
                                                            ? ` / ${organizations.filter(org => !org.is_enabled).length} disabled`
                                                            : ''
                                                    })`
                                                    : "Organizations"
                                            }
                                        >
                                            {organizations &&
                                            organizations.length > 0 ? (
                                                organizations.map((org) => {
                                                    const isDisabled = !org.is_enabled;

                                                    return (
                                                        <Tooltip key={org.id}>
                                                            <TooltipTrigger asChild>
                                                                <CommandItem
                                                                    value={org.name}
                                                                    onSelect={() =>
                                                                        handleOrgSelect(org)
                                                                    }
                                                                    className={cn(
                                                                        "flex items-center",
                                                                        isDisabled
                                                                            ? "cursor-not-allowed opacity-60"
                                                                            : "cursor-pointer"
                                                                    )}
                                                                >
                                                                    <Check
                                                                        className={cn(
                                                                            "mr-2 h-4 w-4 shrink-0",
                                                                            !isGlobalView &&
                                                                                selectedOrg?.id ===
                                                                                    org.id
                                                                                ? "opacity-100"
                                                                                : "opacity-0"
                                                                        )}
                                                                    />
                                                                    <Building2 className="mr-2 h-4 w-4 shrink-0" />
                                                                    <span className={cn(
                                                                        "truncate flex-1",
                                                                        isDisabled && "line-through"
                                                                    )}>
                                                                        {org.name}
                                                                    </span>
                                                                    {isDisabled && (
                                                                        <Badge
                                                                            variant="secondary"
                                                                            className="ml-2 text-xs"
                                                                        >
                                                                            Disabled
                                                                        </Badge>
                                                                    )}
                                                                </CommandItem>
                                                            </TooltipTrigger>
                                                            {isDisabled && (
                                                                <TooltipContent>
                                                                    <p>This organization is disabled</p>
                                                                </TooltipContent>
                                                            )}
                                                        </Tooltip>
                                                    );
                                                })
                                            ) : (
                                                <CommandItem disabled>
                                                    No organizations
                                                </CommandItem>
                                            )}
                                        </CommandGroup>
                                    </>
                                )}
                            </CommandList>
                            <CommandSeparator />
                            <div className="p-2">
                                <label className="flex items-center gap-2 px-2 py-1.5 text-sm text-muted-foreground cursor-pointer hover:bg-accent rounded-sm transition-colors">
                                    <Checkbox
                                        checked={showDisabled}
                                        onCheckedChange={(checked) =>
                                            setShowDisabled(checked === true)
                                        }
                                        disabled={isValidating}
                                    />
                                    <span className="select-none">Show disabled organizations</span>
                                </label>
                            </div>
                            <CommandSeparator />
                            <CommandGroup>
                                <CommandItem
                                    onSelect={handleCreateOrg}
                                    className="cursor-pointer"
                                    disabled={isValidating}
                                >
                                    <Plus className="mr-2 h-4 w-4" />
                                    Create organization
                                </CommandItem>
                            </CommandGroup>
                        </Command>
                    </PopoverContent>
                </Popover>

                {/* Quick nav button - only show when org is selected */}
                {currentOrg && !isGlobalView && (
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-9 w-9"
                                onClick={() => navigate(`/org/${currentOrg.id}`)}
                                aria-label={`Go to ${currentOrg.name}`}
                            >
                                <ArrowRight className="h-4 w-4" />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                            <p>Go to {currentOrg.name}</p>
                        </TooltipContent>
                    </Tooltip>
                )}
            </div>

            <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
                <DialogContent className="sm:max-w-[400px]">
                    <form onSubmit={handleCreateSubmit}>
                        <DialogHeader>
                            <DialogTitle>Create Organization</DialogTitle>
                            <DialogDescription>
                                Create a new organization to start documenting
                                your IT infrastructure.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="py-4">
                            <Label htmlFor="org-name">Organization Name</Label>
                            <Input
                                id="org-name"
                                placeholder="Acme Corporation"
                                value={newOrgName}
                                onChange={(e) => setNewOrgName(e.target.value)}
                                className="mt-2"
                                autoFocus
                            />
                        </div>
                        <DialogFooter>
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => setCreateDialogOpen(false)}
                            >
                                Cancel
                            </Button>
                            <Button
                                type="submit"
                                disabled={createOrganization.isPending}
                            >
                                {createOrganization.isPending && (
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                )}
                                Create
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </>
    );
}
