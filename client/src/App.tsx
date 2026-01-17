import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryProvider } from "@/providers/query-provider";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppLayout } from "@/components/layout/AppLayout";

// Auth pages
import { LoginPage } from "@/pages/auth/LoginPage";
import { RegisterPage } from "@/pages/auth/RegisterPage";
import { SetupPage } from "@/pages/auth/SetupPage";
import { OAuthCallbackPage } from "@/pages/auth/OAuthCallbackPage";

// Main pages
import { DashboardPage } from "@/pages/DashboardPage";
import { OrgHomePage } from "@/pages/org/OrgHomePage";

// Entity pages
import { PasswordsPage } from "@/pages/passwords/PasswordsPage";
import { PasswordDetailPage } from "@/pages/passwords/PasswordDetailPage";
import { ConfigurationsPage } from "@/pages/configurations/ConfigurationsPage";
import { ConfigDetailPage } from "@/pages/configurations/ConfigDetailPage";
import { LocationsPage } from "@/pages/locations/LocationsPage";
import { LocationDetailPage } from "@/pages/locations/LocationDetailPage";
import { DocumentsPage } from "@/pages/documents/DocumentsPage";
import { DocumentDetailPage } from "@/pages/documents/DocumentDetailPage";
import { CustomAssetsPage } from "@/pages/assets/CustomAssetsPage";
import { CustomAssetDetailPage } from "@/pages/assets/CustomAssetDetailPage";

// Audit pages
import { OrgAuditTrailPage, GlobalAuditTrailPage } from "@/pages/audit/AuditTrailPage";

// Organizations pages
import { OrganizationsListPage } from "@/pages/organizations/OrganizationsListPage";
import { OrganizationsPage } from "@/pages/organizations/OrganizationsPage";
import { OrganizationDetailPage } from "@/pages/organizations/OrganizationDetailPage";

// Global pages
import {
  GlobalPage,
  GlobalPasswordsPage,
  GlobalConfigurationsPage,
  GlobalLocationsPage,
  GlobalDocumentsPage,
  GlobalCustomAssetsPage,
} from "@/pages/global";

// Settings pages
import { SettingsPage } from "@/pages/settings/SettingsPage";
import { ProfileSettings } from "@/pages/settings/ProfileSettings";
import { SecuritySettings } from "@/pages/settings/SecuritySettings";
import { ApiKeysSettings } from "@/pages/settings/ApiKeysSettings";
import { ConfigurationTypesSettings } from "@/pages/settings/ConfigurationTypesSettings";
import { ConfigurationStatusesSettings } from "@/pages/settings/ConfigurationStatusesSettings";
import { CustomAssetTypesSettings } from "@/pages/settings/CustomAssetTypesSettings";
import { UsersSettings } from "@/pages/settings/UsersSettings";
import { AISettings } from "@/pages/settings/AISettings";
import { ExportsSettings } from "@/pages/settings/ExportsSettings";
import { OAuthSettings } from "@/pages/settings/OAuthSettings";

function App() {
  return (
    <QueryProvider>
      <TooltipProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/setup" element={<SetupPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/auth/callback/:provider" element={<OAuthCallbackPage />} />

            {/* Protected routes */}
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              {/* Dashboard */}
              <Route path="/" element={<DashboardPage />} />

              {/* Organization routes */}
              <Route path="/org/:orgId" element={<OrgHomePage />} />

              {/* Passwords */}
              <Route path="/org/:orgId/passwords" element={<PasswordsPage />} />
              <Route
                path="/org/:orgId/passwords/:id"
                element={<PasswordDetailPage />}
              />

              {/* Configurations */}
              <Route
                path="/org/:orgId/configurations"
                element={<ConfigurationsPage />}
              />
              <Route
                path="/org/:orgId/configurations/:id"
                element={<ConfigDetailPage />}
              />

              {/* Locations */}
              <Route path="/org/:orgId/locations" element={<LocationsPage />} />
              <Route
                path="/org/:orgId/locations/:id"
                element={<LocationDetailPage />}
              />

              {/* Documents - nested routes for shared sidebar */}
              <Route path="/org/:orgId/documents" element={<DocumentsPage />}>
                <Route path=":id" element={<DocumentDetailPage />} />
              </Route>

              {/* Custom Assets */}
              <Route path="/org/:orgId/assets" element={<CustomAssetsPage />} />
              <Route
                path="/org/:orgId/assets/:typeId"
                element={<CustomAssetsPage />}
              />
              <Route
                path="/org/:orgId/assets/:typeId/:id"
                element={<CustomAssetDetailPage />}
              />

              {/* Audit Trail */}
              <Route path="/org/:orgId/audit-trail" element={<OrgAuditTrailPage />} />

              {/* Organizations */}
              <Route path="/organizations" element={<OrganizationsListPage />} />
              <Route path="/admin/organizations" element={<OrganizationsPage />} />
              <Route path="/admin/organizations/:id" element={<OrganizationDetailPage />} />

              {/* Global view */}
              <Route path="/global" element={<GlobalPage />} />
              <Route path="/global/passwords" element={<GlobalPasswordsPage />} />
              <Route path="/global/configurations" element={<GlobalConfigurationsPage />} />
              <Route path="/global/locations" element={<GlobalLocationsPage />} />
              <Route path="/global/documents" element={<GlobalDocumentsPage />} />
              <Route path="/global/assets/:typeId" element={<GlobalCustomAssetsPage />} />
              <Route path="/global/audit-trail" element={<GlobalAuditTrailPage />} />

              {/* Settings - nested routes */}
              <Route path="/settings" element={<SettingsPage />}>
                <Route index element={<Navigate to="profile" replace />} />
                <Route path="profile" element={<ProfileSettings />} />
                <Route path="security" element={<SecuritySettings />} />
                <Route path="api-keys" element={<ApiKeysSettings />} />
                <Route path="configuration-types" element={<ConfigurationTypesSettings />} />
                <Route path="configuration-statuses" element={<ConfigurationStatusesSettings />} />
                <Route path="custom-asset-types" element={<CustomAssetTypesSettings />} />
                <Route path="users" element={<UsersSettings />} />
                <Route path="ai" element={<AISettings />} />
                <Route path="exports" element={<ExportsSettings />} />
                <Route path="oauth" element={<OAuthSettings />} />
              </Route>

              {/* Legacy redirects */}
              <Route path="/personal" element={<Navigate to="/settings" replace />} />
              <Route path="/personal/*" element={<Navigate to="/settings" replace />} />
              <Route path="/admin" element={<Navigate to="/settings" replace />} />
              <Route path="/admin/*" element={<Navigate to="/settings" replace />} />
            </Route>

            {/* Catch all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster />
      </TooltipProvider>
    </QueryProvider>
  );
}

export default App;
