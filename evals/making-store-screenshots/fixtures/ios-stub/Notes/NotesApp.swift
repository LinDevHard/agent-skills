import SwiftUI

@main
struct NotesApp: App {
    var body: some Scene { WindowGroup { ContentView() } }
}

struct Note: Identifiable { let id = UUID(); let title: String; let body: String }

struct ContentView: View {
    let notes = [
        Note(title: "Groceries", body: "Milk, apples, coffee beans"),
        Note(title: "Trip ideas", body: "Lisbon in May, Porto by train"),
        Note(title: "Book club", body: "Chapter 4 questions"),
    ]
    var body: some View {
        TabView {
            NavigationStack {
                List(notes) { note in
                    NavigationLink(destination: NoteView(note: note)) {
                        VStack(alignment: .leading) { Text(note.title).font(.headline); Text(note.body).foregroundStyle(.secondary) }
                    }
                }.navigationTitle("Notes")
            }.tabItem { Label("Notes", systemImage: "note.text") }
            NavigationStack { Form { Toggle("iCloud sync", isOn: .constant(true)); Toggle("Dark mode", isOn: .constant(false)) }
                .navigationTitle("Settings") }.tabItem { Label("Settings", systemImage: "gear") }
        }
    }
}

struct NoteView: View {
    let note: Note
    var body: some View { ScrollView { Text(note.body).padding() }.navigationTitle(note.title) }
}
