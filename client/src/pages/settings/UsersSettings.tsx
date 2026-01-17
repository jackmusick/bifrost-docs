import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Loader2,
  Users,
  Trash2,
  UserPlus,
  Crown,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  adminApi,
  type OrganizationUser,
} from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth.store";

const createUserSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  role: z.enum(["contributor", "administrator", "reader"], {
    message: "Please select a role",
  }),
});

type CreateUserFormData = z.infer<typeof createUserSchema>;

export function UsersSettings() {
  const queryClient = useQueryClient();
  const { user: currentUser } = useAuthStore();
  const [createUserDialogOpen, setCreateUserDialogOpen] = useState(false);
  const [transferDialogOpen, setTransferDialogOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  const { data: users, isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => adminApi.listUsers().then((r) => r.data),
  });

  const createUserMutation = useMutation({
    mutationFn: (data: CreateUserFormData) =>
      adminApi.createUser(data).then((r) => r.data),
    onSuccess: () => {
      toast.success("User created successfully. They can now login via SSO.");
      setCreateUserDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || "Failed to create user";
      toast.error(message);
    },
  });

  const removeUserMutation = useMutation({
    mutationFn: (userId: string) => adminApi.removeUser(userId),
    onSuccess: () => {
      toast.success("User removed");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: () => {
      toast.error("Failed to remove user");
    },
  });

  const transferOwnershipMutation = useMutation({
    mutationFn: (userId: string) => adminApi.transferOwnership(userId),
    onSuccess: () => {
      toast.success("Ownership transferred");
      setTransferDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: () => {
      toast.error("Failed to transfer ownership");
    },
  });

  const createUserForm = useForm<CreateUserFormData>({
    resolver: zodResolver(createUserSchema),
    defaultValues: {
      email: "",
      role: "contributor",
    },
  });

  function formatDate(dateString: string) {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                User Management
              </CardTitle>
              <CardDescription>
                Manage users in your organization
              </CardDescription>
            </div>
            <Button onClick={() => setCreateUserDialogOpen(true)}>
              <UserPlus className="mr-2 h-4 w-4" />
              New User
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {users && users.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="w-[100px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user: OrganizationUser) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium flex items-center gap-2">
                          {user.name}
                          {user.id === currentUser?.id && (
                            <Badge variant="outline" className="text-xs">
                              You
                            </Badge>
                          )}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {user.email}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          user.role === "owner"
                            ? "default"
                            : user.role === "admin"
                            ? "secondary"
                            : "outline"
                        }
                      >
                        {user.role === "owner" && (
                          <Crown className="mr-1 h-3 w-3" />
                        )}
                        {user.role}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={user.is_active ? "default" : "secondary"}
                      >
                        {user.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatDate(user.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {user.id !== currentUser?.id && user.role !== "owner" && (
                          <>
                            <Button
                              variant="ghost"
                              size="icon"
                              title="Transfer ownership"
                              onClick={() => {
                                setSelectedUserId(user.id);
                                setTransferDialogOpen(true);
                              }}
                            >
                              <Crown className="h-4 w-4" />
                            </Button>
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  title="Remove user"
                                >
                                  <Trash2 className="h-4 w-4 text-destructive" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Remove User</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Are you sure you want to remove {user.name}{" "}
                                    from the organization? They will lose access
                                    to all organization data.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() =>
                                      removeUserMutation.mutate(user.id)
                                    }
                                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                  >
                                    Remove
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              No users found.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Create User Dialog */}
      <Dialog open={createUserDialogOpen} onOpenChange={setCreateUserDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New User</DialogTitle>
            <DialogDescription>
              Create a new user who can login via SSO. They will receive their role immediately.
            </DialogDescription>
          </DialogHeader>

          <Form {...createUserForm}>
            <form
              onSubmit={createUserForm.handleSubmit((data) =>
                createUserMutation.mutate(data)
              )}
              className="space-y-4"
            >
              <FormField
                control={createUserForm.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email Address</FormLabel>
                    <FormControl>
                      <Input
                        type="email"
                        placeholder="user@example.com"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={createUserForm.control}
                name="role"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Role</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a role" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="contributor">Contributor</SelectItem>
                        <SelectItem value="administrator">Administrator</SelectItem>
                        <SelectItem value="reader">Reader</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setCreateUserDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={createUserMutation.isPending}>
                  {createUserMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Create User
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Transfer Ownership Dialog */}
      <AlertDialog open={transferDialogOpen} onOpenChange={setTransferDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Transfer Ownership</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to transfer ownership? This action cannot be
              undone. You will become a regular admin and the selected user will
              become the owner.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (selectedUserId) {
                  transferOwnershipMutation.mutate(selectedUserId);
                }
              }}
              disabled={transferOwnershipMutation.isPending}
            >
              {transferOwnershipMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Transfer Ownership
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
