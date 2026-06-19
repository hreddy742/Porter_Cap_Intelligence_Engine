import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { Layout } from "./components/Layout";
import { Home } from "./pages/Home";
import { Search } from "./pages/Search";
import { CompanyProfile } from "./pages/CompanyProfile";
import { RecentBusinesses } from "./pages/RecentBusinesses";
import { RecentBusinessDetail } from "./pages/RecentBusinessDetail";
import "./styles.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: "search", element: <Search /> },
      { path: "recent", element: <RecentBusinesses /> },
      { path: "recent/:state/:entityId", element: <RecentBusinessDetail /> },
      { path: "company/:companyId", element: <CompanyProfile /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);
