import { api } from "./client"
import type { MemberResponse, SocialSecurityComparison } from "./types"

export const membersApi = {
  list: () => api.get<MemberResponse[]>("/members"),

  get: (id: string) => api.get<MemberResponse>(`/members/${id}`),

  socialSecurityEstimate: (id: string, monthlyBenefitAtFra: string) =>
    api.get<SocialSecurityComparison>(
      `/members/${id}/social-security-estimate?monthly_benefit_at_fra=${encodeURIComponent(
        monthlyBenefitAtFra,
      )}`,
    ),

  create: (data: {
    display_name: string
    role?: "primary" | "partner" | "dependent"
    date_of_birth?: string | null
    retirement_target_age?: number | null
  }) => api.post<MemberResponse>("/members", data),

  update: (
    id: string,
    data: Partial<{
      display_name: string
      role: "primary" | "partner" | "dependent"
      date_of_birth: string | null
      retirement_target_age: number | null
      is_active: boolean
    }>,
  ) => api.patch<MemberResponse>(`/members/${id}`, data),

  deactivate: (id: string) => api.delete(`/members/${id}`),

  updateDashboardLayout: (
    id: string,
    data: { widgets: { id: string; visible: boolean; order: number }[] },
  ) => api.patch<MemberResponse>(`/members/${id}/dashboard-layout`, data),
}
