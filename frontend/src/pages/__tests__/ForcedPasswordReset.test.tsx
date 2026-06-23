import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { vi, describe, it, expect, beforeEach } from "vitest"
import { ApiError } from "@/api/client"
import { authApi } from "@/api/auth"
import ForcedPasswordReset from "@/pages/ForcedPasswordReset"

const navigate = vi.fn()
const clearMustChangePassword = vi.fn()

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => navigate,
}))

vi.mock("@/api/auth", () => ({
  authApi: { changePassword: vi.fn() },
}))

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn((selector: (s: { clearMustChangePassword: () => void }) => unknown) =>
    selector({ clearMustChangePassword }),
  ),
}))

describe("ForcedPasswordReset", () => {
  beforeEach(() => vi.clearAllMocks())

  async function fill(current: string, next: string, confirm: string) {
    render(<ForcedPasswordReset />)
    await userEvent.type(screen.getByLabelText(/Temporary password/i), current)
    await userEvent.type(screen.getByLabelText(/^New password$/i), next)
    await userEvent.type(screen.getByLabelText(/Confirm new password/i), confirm)
    await userEvent.click(screen.getByRole("button", { name: /Set password/i }))
  }

  it("changes the password, clears the flag, and navigates home on success", async () => {
    vi.mocked(authApi.changePassword).mockResolvedValue(undefined)
    await fill("temp-pass-123", "BrandNewPass1", "BrandNewPass1")
    await waitFor(() =>
      expect(authApi.changePassword).toHaveBeenCalledWith("temp-pass-123", "BrandNewPass1"),
    )
    expect(clearMustChangePassword).toHaveBeenCalled()
    expect(navigate).toHaveBeenCalledWith({ to: "/" })
  })

  it("blocks submission when the two new passwords don't match", async () => {
    await fill("temp-pass-123", "BrandNewPass1", "Different9")
    await waitFor(() => expect(screen.getByText(/don't match/i)).toBeInTheDocument())
    expect(authApi.changePassword).not.toHaveBeenCalled()
  })

  it("surfaces a clear error when the temporary password is wrong (401)", async () => {
    vi.mocked(authApi.changePassword).mockRejectedValue(new ApiError(401, "bad"))
    await fill("wrong-temp", "BrandNewPass1", "BrandNewPass1")
    await waitFor(() =>
      expect(screen.getByText(/temporary password is incorrect/i)).toBeInTheDocument(),
    )
    expect(clearMustChangePassword).not.toHaveBeenCalled()
  })
})
