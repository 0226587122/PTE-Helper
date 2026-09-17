import { Route, Routes } from "react-router-dom";

import AdminQuestion from "./admin/AdminQuestion";
import AdminQuestions from "./admin/AdminQuestions";
import { AdminLayout } from "./admin/AdminLayout";
import AdminSummary from "./admin/AdminSummary";
import { RequireAdmin, RequireAuth } from "./components/Guards";
import { Layout } from "./components/Layout";
import Home from "./pages/Home";
import Practice from "./pages/Practice";
import Results from "./pages/Results";
import SignIn from "./pages/SignIn";
import SignUp from "./pages/SignUp";

function NotFound() {
  return (
    <div>
      <h1>Page not found</h1>
      <p>
        That page doesn't exist. <a href="/">Go back to practice</a>.
      </p>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route
          index
          element={
            <RequireAuth>
              <Home />
            </RequireAuth>
          }
        />
        <Route path="signin" element={<SignIn />} />
        <Route path="signup" element={<SignUp />} />
        <Route
          path="practice/:setId"
          element={
            <RequireAuth>
              <Practice />
            </RequireAuth>
          }
        />
        <Route
          path="results/:setId"
          element={
            <RequireAuth>
              <Results />
            </RequireAuth>
          }
        />
        <Route
          path="admin"
          element={
            <RequireAdmin>
              <AdminLayout />
            </RequireAdmin>
          }
        >
          <Route index element={<AdminSummary />} />
          <Route path="questions" element={<AdminQuestions />} />
          <Route path="questions/:id" element={<AdminQuestion />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
