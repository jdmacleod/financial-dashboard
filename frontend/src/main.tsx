import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { QueryClientProvider } from "@tanstack/react-query"
import { RouterProvider } from "@tanstack/react-router"
import { queryClient } from "./lib/queryClient"
import { router } from "./router"
import "./index.css"
import "@fontsource/archivo/400.css"
import "@fontsource/archivo/500.css"
import "@fontsource/archivo/600.css"
import "@fontsource/archivo/700.css"
import "@fontsource/spectral/600.css"
import "./stores/themeStore" // applies data-theme attribute on <html> on startup

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
