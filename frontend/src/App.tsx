import { Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Validation } from "./pages/Validation";
import { CategoryPage } from "./pages/CategoryPage";
import { TestDetail } from "./pages/TestDetail";
import { Reports } from "./pages/Reports";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/validation" element={<Validation />} />
        <Route path="/category/:category" element={<CategoryPage />} />
        <Route path="/test/:id" element={<TestDetail />} />
        <Route path="/reports" element={<Reports />} />
      </Route>
    </Routes>
  );
}
