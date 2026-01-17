import { Link } from "react-router-dom";
import { Globe, KeyRound, Server, MapPin, FileText, Layers, ArrowRight } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useGlobalSidebarData } from "@/hooks/useGlobalData";

export function GlobalPage() {
  const { data: sidebarData, isLoading } = useGlobalSidebarData();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Globe className="h-8 w-8" />
          Global View
        </h1>
        <p className="text-muted-foreground mt-1">
          View and search data across all organizations
        </p>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-4 w-48" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <>
          {/* Core Entity Cards */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Core Assets</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <Link to="/global/passwords">
                <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <KeyRound className="h-5 w-5 text-primary" />
                      Passwords
                    </CardTitle>
                    <CardDescription>Credentials across all organizations</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <span className="text-2xl font-bold">
                        {sidebarData?.passwords_count.toLocaleString() ?? 0}
                      </span>
                      <ArrowRight className="h-5 w-5 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>
              </Link>

              <Link to="/global/locations">
                <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <MapPin className="h-5 w-5 text-primary" />
                      Locations
                    </CardTitle>
                    <CardDescription>Physical and virtual locations</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <span className="text-2xl font-bold">
                        {sidebarData?.locations_count.toLocaleString() ?? 0}
                      </span>
                      <ArrowRight className="h-5 w-5 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>
              </Link>

              <Link to="/global/documents">
                <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <FileText className="h-5 w-5 text-primary" />
                      Documents
                    </CardTitle>
                    <CardDescription>Documentation across all organizations</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <span className="text-2xl font-bold">
                        {sidebarData?.documents_count.toLocaleString() ?? 0}
                      </span>
                      <ArrowRight className="h-5 w-5 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </div>
          </div>

          {/* Configuration Types */}
          {sidebarData?.configuration_types && sidebarData.configuration_types.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold">Configurations</h2>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {sidebarData.configuration_types.map((type) => (
                  <Link key={type.id} to={`/global/configurations?type=${type.id}`}>
                    <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-lg">
                          <Server className="h-5 w-5 text-primary" />
                          {type.name}
                        </CardTitle>
                        <CardDescription>Configuration items</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-center justify-between">
                          <span className="text-2xl font-bold">
                            {type.count.toLocaleString()}
                          </span>
                          <ArrowRight className="h-5 w-5 text-muted-foreground" />
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Custom Asset Types */}
          {sidebarData?.custom_asset_types && sidebarData.custom_asset_types.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold">Custom Assets</h2>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {sidebarData.custom_asset_types.map((type) => (
                  <Link key={type.id} to={`/global/assets/${type.id}`}>
                    <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-lg">
                          <Layers className="h-5 w-5 text-primary" />
                          {type.name}
                        </CardTitle>
                        <CardDescription>Custom asset items</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-center justify-between">
                          <span className="text-2xl font-bold">
                            {type.count.toLocaleString()}
                          </span>
                          <ArrowRight className="h-5 w-5 text-muted-foreground" />
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
