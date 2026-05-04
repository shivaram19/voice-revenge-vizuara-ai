"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, UserPlus, Phone, Mail, MoreVertical } from "lucide-react";
import { listStudents, type Student, type StudentListResponse } from "@/lib/api";

export default function StudentsDirectoryPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [meta, setMeta] = useState<{ total: number; page: number; page_size: number }>({ total: 0, page: 1, page_size: 20 });
  const [search, setSearch] = useState("");
  const [grade, setGrade] = useState("");
  const [loading, setLoading] = useState(true);

  const loadStudents = useCallback(async () => {
    setLoading(true);
    try {
      const res: StudentListResponse = await listStudents({
        page: meta.page,
        page_size: meta.page_size,
        search: search || undefined,
        grade: grade || undefined,
      });
      setStudents(res.items);
      setMeta({ total: res.total, page: res.page, page_size: res.page_size });
    } catch (e) {
      console.error("Failed to load students", e);
    } finally {
      setLoading(false);
    }
  }, [meta.page, meta.page_size, search, grade]);

  useEffect(() => {
    loadStudents();
  }, [loadStudents]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setMeta((m) => ({ ...m, page: 1 }));
  };

  const handleGradeChange = (value: string) => {
    setGrade(value === "All Grades" ? "" : value);
    setMeta((m) => ({ ...m, page: 1 }));
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Student Directory</h1>
          <p className="text-slate-400 mt-1">Manage contacts and view automated outreach history.</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium transition-colors shadow-lg shadow-indigo-500/20">
          <UserPlus className="w-4 h-4" />
          Add Student
        </button>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col shadow-sm">
        {/* Toolbar */}
        <div className="p-4 border-b border-slate-800/60 flex items-center justify-between bg-slate-900">
          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 w-80 focus-within:border-indigo-500/50 transition-colors">
            <Search className="w-4 h-4 text-slate-500 mr-2" />
            <input
              type="text"
              placeholder="Search by name, grade, or parent..."
              className="bg-transparent border-none outline-none text-sm w-full text-slate-200 placeholder:text-slate-500"
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <select
              className="bg-slate-950 border border-slate-800 text-slate-300 text-sm rounded-lg px-3 py-2 outline-none"
              value={grade || "All Grades"}
              onChange={(e) => handleGradeChange(e.target.value)}
            >
              <option>All Grades</option>
              <option>9th Grade</option>
              <option>10th Grade</option>
              <option>11th Grade</option>
              <option>12th Grade</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-950/50 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800/60">
                <th className="px-6 py-4 font-medium">Student Name</th>
                <th className="px-6 py-4 font-medium">Grade</th>
                <th className="px-6 py-4 font-medium">Primary Contact</th>
                <th className="px-6 py-4 font-medium">Attendance Status</th>
                <th className="px-6 py-4 font-medium">Recent AI Interaction</th>
                <th className="px-6 py-4 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading && (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                    <div className="flex items-center justify-center">
                      <div className="animate-spin w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full mr-2" />
                      Loading students...
                    </div>
                  </td>
                </tr>
              )}
              {!loading && students.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                    No students found.
                  </td>
                </tr>
              )}
              {students.map((student) => (
                <tr key={student.id} className="hover:bg-slate-800/20 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="font-medium text-slate-200">{student.name}</div>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-400">
                    <span className="px-2 py-1 rounded bg-slate-800 text-slate-300">{student.grade}</span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-slate-200 font-medium">{student.parent_name}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{student.parent_phone}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${student.attendance_status === 'Present' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                      {student.attendance_status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-400">
                    {student.recent_call_summary}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-1.5 text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 rounded" title="Call Parent">
                        <Phone className="w-4 h-4" />
                      </button>
                      <button className="p-1.5 text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 rounded" title="Message">
                        <Mail className="w-4 h-4" />
                      </button>
                      <button className="p-1.5 text-slate-400 hover:text-slate-200 rounded">
                        <MoreVertical className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="p-4 border-t border-slate-800/60 bg-slate-900 flex items-center justify-between text-sm text-slate-400">
          <div>
            Showing {students.length > 0 ? (meta.page - 1) * meta.page_size + 1 : 0} to{" "}
            {Math.min(meta.page * meta.page_size, meta.total)} of {meta.total} students
          </div>
          <div className="flex gap-2">
            <button
              className="px-3 py-1 rounded border border-slate-800 hover:bg-slate-800 disabled:opacity-50"
              disabled={meta.page <= 1}
              onClick={() => setMeta((m) => ({ ...m, page: m.page - 1 }))}
            >
              Previous
            </button>
            <button
              className="px-3 py-1 rounded border border-slate-800 hover:bg-slate-800 disabled:opacity-50"
              disabled={meta.page * meta.page_size >= meta.total}
              onClick={() => setMeta((m) => ({ ...m, page: m.page + 1 }))}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
