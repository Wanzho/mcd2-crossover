// Native GitHub updater. Uses Cocoa, Foundation and CryptoKit only.
// Update flow follows wasdmod (Copyright 2026 Wanzho, MIT).
import Cocoa
import CryptoKit

struct UpdateVersion: Comparable {
    let numbers: [Int]
    let preview: [String]?
    init?(_ text: String) {
        let text = text.hasPrefix("v") ? String(text.dropFirst()) : text
        let parts = text.split(separator: "-", maxSplits: 1, omittingEmptySubsequences: false)
        let core = parts[0].split(separator: ".", omittingEmptySubsequences: false)
        guard !core.isEmpty, core.count <= 4, core.allSatisfy({ !$0.isEmpty && $0.allSatisfy(\.isNumber) && Int($0) != nil }) else { return nil }
        numbers = core.map { Int($0)! }
        if parts.count == 2 {
            let ids = parts[1].split(separator: ".", omittingEmptySubsequences: false).map(String.init)
            guard ids.allSatisfy({ !$0.isEmpty && $0.utf8.allSatisfy { (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0) || $0 == 45 } }) else { return nil }
            preview = ids
        } else { preview = nil }
    }
    static func == (a: Self, b: Self) -> Bool { !(a < b) && !(b < a) }
    static func < (a: Self, b: Self) -> Bool {
        for i in 0..<max(a.numbers.count,b.numbers.count) {
            let x = i < a.numbers.count ? a.numbers[i] : 0, y = i < b.numbers.count ? b.numbers[i] : 0
            if x != y { return x < y }
        }
        guard let x = a.preview else { return false }
        guard let y = b.preview else { return true }
        for i in 0..<min(x.count,y.count) where x[i] != y[i] {
            if let p = Int(x[i]), let q = Int(y[i]) { return p < q }
            if Int(x[i]) != nil { return true }
            if Int(y[i]) != nil { return false }
            return x[i] < y[i]
        }
        return x.count < y.count
    }
}
struct UpdateManifest: Codable {
    let schema: Int, bundleIdentifier: String, version: String, build: String
    let archive: String, bytes: Int64, sha256: String, minimumSystemVersion: String
    let notes: String, important: Bool
}
struct UpdateProblem: LocalizedError {
    let message: String
    var errorDescription: String? { message }
    init(_ message: String) { self.message = message }
}
struct UpdateSource {
    let repository: String
    var api: URL { URL(string: "https://api.github.com/repos/\(repository)/releases?per_page=20")! }
    var root: String { "https://github.com/\(repository)/releases/download/" }
    func allowed(_ u: URL) -> Bool {
        guard u.user == nil, u.password == nil else { return false }
        #if UPDATER_TEST
        if u.scheme == "http", u.host == "127.0.0.1", u.port == 18765 { return true }
        #endif
        return u.scheme == "https" && (u.port == nil || u.port == 443) &&
            ["api.github.com","github.com","objects.githubusercontent.com","release-assets.githubusercontent.com","github-releases.githubusercontent.com"].contains(u.host?.lowercased() ?? "")
    }
    func asset(_ u: URL) -> Bool {
        #if UPDATER_TEST
        if u.scheme == "http", u.host == "127.0.0.1", u.port == 18765 { return true }
        #endif
        return allowed(u) && u.absoluteString.hasPrefix(root) && u.query == nil && u.fragment == nil &&
            !u.pathComponents.contains("..") && !u.absoluteString.contains("%") && !u.absoluteString.contains("\\")
    }
}
// A bounded, ephemeral download with restricted redirects. Never stores cookies.
final class UpdateFetch: NSObject, URLSessionDownloadDelegate {
    let source: UpdateSource, limit: Int64, completion: (Result<URL,Error>) -> Void
    var session: URLSession?, task: URLSessionDownloadTask?, saved: URL?, failure: Error?
    init(url: URL, source: UpdateSource, limit: Int64, completion: @escaping (Result<URL,Error>) -> Void) {
        self.source = source; self.limit = limit; self.completion = completion
        super.init()
        guard source.allowed(url) else { DispatchQueue.main.async { completion(.failure(UpdateProblem("The update address is not allowed."))) }; return }
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 25; config.timeoutIntervalForResource = 600
        session = URLSession(configuration: config, delegate: self, delegateQueue: nil)
        var request = URLRequest(url: url)
        request.setValue("Crossover-Updater/1",forHTTPHeaderField:"User-Agent")
        request.setValue("application/vnd.github+json",forHTTPHeaderField:"Accept")
        task = session!.downloadTask(with: request); task!.resume()
    }
    func cancel() { task?.cancel() }
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        if let u = newRequest.url, source.allowed(u) { completionHandler(newRequest) }
        else { failure = UpdateProblem("The update download redirected outside GitHub."); completionHandler(nil) }
    }
    func urlSession(_ session: URLSession, downloadTask: URLSessionDownloadTask, didWriteData bytesWritten: Int64,
                    totalBytesWritten: Int64, totalBytesExpectedToWrite: Int64) {
        if totalBytesWritten > limit || totalBytesExpectedToWrite > limit {
            failure = UpdateProblem("The update download is larger than expected."); downloadTask.cancel()
        }
    }
    func urlSession(_ session: URLSession, downloadTask: URLSessionDownloadTask, didFinishDownloadingTo location: URL) {
        guard failure == nil else { return }
        guard (downloadTask.response as? HTTPURLResponse)?.statusCode == 200 else {
            failure = UpdateProblem("GitHub could not provide the update. Try again later."); return
        }
        do {
            let size = try location.resourceValues(forKeys:[.fileSizeKey]).fileSize ?? 0
            guard size > 0 && Int64(size) <= limit else { throw UpdateProblem("The update download has an invalid size.") }
            let folder = FileManager.default.temporaryDirectory.appendingPathComponent("crossover-download-"+UUID().uuidString)
            try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:false,attributes:[.posixPermissions:0o700])
            let file = folder.appendingPathComponent("download")
            try FileManager.default.moveItem(at:location,to:file); saved = file
        } catch { failure = error }
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        session.finishTasksAndInvalidate(); self.session = nil; self.task = nil
        let result: Result<URL,Error>
        if let error = failure ?? error { result = .failure(error); if let saved { try? FileManager.default.removeItem(at:saved.deletingLastPathComponent()) } }
        else if let saved { result = .success(saved) }
        else { result = .failure(UpdateProblem("The update download is empty.")) }
        DispatchQueue.main.async { self.completion(result) }
    }
}
func updateRun(_ command: String, _ args: [String]) throws -> String {
    let task = Process(); task.executableURL = URL(fileURLWithPath:command); task.arguments = args
    let pipe = Pipe(); task.standardOutput = pipe; task.standardError = pipe
    try task.run()
    let data = pipe.fileHandleForReading.readDataToEndOfFile(); task.waitUntilExit()
    guard task.terminationStatus == 0 else { throw UpdateProblem("Could not complete the update validation or installation.") }
    return String(decoding:data,as:UTF8.self)
}
func updateGameName(_ command: String) -> Bool {
    let name = command.trimmingCharacters(in:.whitespacesAndNewlines).replacingOccurrences(of:"\\",with:"/").split(separator:"/").last?.lowercased() ?? ""
    return ["dungeons-win64-shipping.exe","dungeons-wingdk-shipping.exe","dungeons.exe","mcd1-auth-broker","mcd1-native-auth-relay"].contains(name)
}
func updateGameRunning() -> Bool {
    // CrossOver's proc_pidpath can misleadingly say explorer.exe; comm has the Windows name.
    guard let names = try? updateRun("/bin/ps",["-axo","comm="]), !names.isEmpty, names.utf8.count < 2_000_000 else { return true }
    return names.split(separator:"\n").contains { updateGameName(String($0)) }
}
func verifiedManifest(_ data: Data, signature: Data, publicKey: Data, bundleID: String) throws -> UpdateManifest {
    guard let key = try? Curve25519.Signing.PublicKey(rawRepresentation:publicKey),
          key.isValidSignature(signature,for:data) else { throw UpdateProblem("The update signature is invalid. Nothing was installed.") }
    let m = try JSONDecoder().decode(UpdateManifest.self,from:data)
    guard m.schema == 1, m.bundleIdentifier == bundleID, UpdateVersion(m.version) != nil,
          UpdateVersion(m.build) != nil, UpdateVersion(m.minimumSystemVersion) != nil,
          m.archive.hasSuffix(".zip"), m.archive.utf8.allSatisfy({ (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0) || "._-".utf8.contains($0) }),
          m.bytes > 0, m.bytes <= 512 * 1024 * 1024, m.sha256.count == 64,
          m.sha256.allSatisfy(\.isHexDigit), m.notes.utf8.count < 32768 else { throw UpdateProblem("The update information is not valid for this app.") }
    return m
}
@objc(CrossoverUpdater) public final class CrossoverUpdater: NSObject, NSMenuItemValidation, NSWindowDelegate {
    private static let instance = CrossoverUpdater()
    @objc public class func shared() -> CrossoverUpdater { instance }
    var busyCheck: (() -> Bool)?
    var checking = false, updating = false, replacing = false, started = false
    var fetch: UpdateFetch?, wait: Timer?, panel: NSWindow?, status: NSTextField?, cancelButton: NSButton?
    var operation = UUID(), temporary: [URL] = []
    var source: UpdateSource { UpdateSource(repository:Bundle.main.object(forInfoDictionaryKey:"CrossoverUpdateRepository") as? String ?? "") }
    var version: String { Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? "0" }
    var build: String { Bundle.main.object(forInfoDictionaryKey:"CFBundleVersion") as? String ?? "0" }
    var current: URL { Bundle.main.bundleURL.resolvingSymlinksInPath() }
    var busy: Bool { busyCheck?() == true || updateGameRunning() }
    @objc(startWithBusyCheck:) func start(_ check: @escaping () -> Bool) {
        busyCheck = check
        guard !started else { return }; started = true
        #if UPDATER_TEST
        if CommandLine.arguments.contains("--crossover-updated"), Bundle.main.object(forInfoDictionaryKey:"CrossoverTestFailRelaunch") as? Bool == true { return }
        #endif
        if acknowledgeRelaunch() { return }
        #if UPDATER_TEST
        if (ProcessInfo.processInfo.environment["CROSSOVER_UPDATE_TEST"] == "install" || Bundle.main.object(forInfoDictionaryKey:"CrossoverTestInstall") as? Bool == true) {
            DispatchQueue.main.async { self.checkForUpdates(nil) }; return
        }
        #endif
        let prefs = UserDefaults.standard
        guard prefs.object(forKey:"CrossoverAutomaticallyCheck") as? Bool != false else { return }
        if let last = prefs.object(forKey:"CrossoverLastUpdateCheck") as? Date, Date().timeIntervalSince(last) < 86400 { return }
        DispatchQueue.main.asyncAfter(deadline:.now()+8) { if !self.busy { self.check(manual:false) } }
    }
    @objc func addItems(to menu: NSMenu) {
        let item = menu.addItem(withTitle:NSLocalizedString("Check for Updates…",comment:""),action:#selector(checkForUpdates(_:)),keyEquivalent:""); item.target = self
        let automatic = menu.addItem(withTitle:NSLocalizedString("Automatically Check for Updates",comment:""),action:#selector(toggleAutomatic(_:)),keyEquivalent:""); automatic.target = self
    }
    @objc(addItemsToMenu:) func addItemsToMenu(_ menu: NSMenu) { addItems(to:menu) }
    @objc func toggleAutomatic(_ sender: Any?) { UserDefaults.standard.set(UserDefaults.standard.object(forKey:"CrossoverAutomaticallyCheck") as? Bool == false,forKey:"CrossoverAutomaticallyCheck") }
    public func validateMenuItem(_ item: NSMenuItem) -> Bool {
        if item.action == #selector(toggleAutomatic(_:)) { item.state = UserDefaults.standard.object(forKey:"CrossoverAutomaticallyCheck") as? Bool == false ? .off : .on }
        return !checking && !updating
    }
    @objc func allowsNewOperation() -> Bool {
        if !updating { return true }
        showMessage("An update is in progress","Finish or cancel the update before starting the game or changing its setup."); return false
    }
    @objc func mustWaitBeforeQuitting() -> Bool { replacing }
    @objc func checkForUpdates(_ sender: Any?) { check(manual:true) }
    func showMessage(_ title: String, _ text: String) {
        #if UPDATER_TEST
        if (ProcessInfo.processInfo.environment["CROSSOVER_UPDATE_TEST"] != nil || Bundle.main.object(forInfoDictionaryKey:"CrossoverTestInstall") as? Bool == true) { updateTestLog("\(title): \(text)"); return }
        #endif
        let alert = NSAlert(); alert.messageText = title; alert.informativeText = text; alert.runModal()
    }
    func request(_ url: URL, limit: Int64, done: @escaping (Result<Data,Error>) -> Void) {
        fetch = UpdateFetch(url:url,source:source,limit:limit) { result in
            done(result.flatMap { file in
                defer { try? FileManager.default.removeItem(at:file.deletingLastPathComponent()) }
                return Result { try Data(contentsOf:file) }
            })
        }
    }
    func check(manual: Bool) {
        guard !checking && !updating else { return }
        guard ["Wanzho/mcd1-crossover","Wanzho/mcd2-crossover"].contains(source.repository) else { return }
        checking = true
        var api = source.api
        #if UPDATER_TEST
        if let text = ProcessInfo.processInfo.environment["CROSSOVER_UPDATE_API"] ?? Bundle.main.object(forInfoDictionaryKey:"CrossoverTestAPI") as? String, let url = URL(string:text),source.allowed(url) { api = url }
        #endif
        request(api,limit:2*1024*1024) { result in
            do {
                let data = try result.get()
                let rows = try JSONSerialization.jsonObject(with:data) as? [[String:Any]] ?? []
                let preview = Bundle.main.object(forInfoDictionaryKey:"CrossoverUpdatePreviews") as? Bool == true
                let eligible = rows.filter { $0["draft"] as? Bool != true && (preview || $0["prerelease"] as? Bool != true) }
                    .compactMap { row -> (UpdateVersion,[String:Any])? in
                        guard let tag = row["tag_name"] as? String, let v = UpdateVersion(tag),v > UpdateVersion(self.version)! else { return nil }; return (v,row)
                    }.sorted { $0.0 > $1.0 }
                guard let release = eligible.first?.1 else {
                    self.checking = false; UserDefaults.standard.set(Date(),forKey:"CrossoverLastUpdateCheck")
                    if manual { self.showMessage("You're up to date", "\(self.version) is the newest available version.") }; return
                }
                let assets = release["assets"] as? [[String:Any]] ?? []
                func asset(_ name: String) -> URL? {
                    guard let row = assets.first(where: { $0["name"] as? String == name }),let text = row["browser_download_url"] as? String,let u = URL(string:text),self.source.asset(u) else { return nil }; return u
                }
                guard let manifest = asset("update.json"),let signature = asset("update.sig") else { throw UpdateProblem("This release does not contain a signed automatic update yet.") }
                self.request(manifest,limit:65536) { result in
                    do {
                        let manifestData = try result.get()
                        self.request(signature,limit:1024) { result in
                            do {
                                let encoded = String(decoding:try result.get(),as:UTF8.self).trimmingCharacters(in:.whitespacesAndNewlines)
                                guard let signature = Data(base64Encoded:encoded),let text = Bundle.main.object(forInfoDictionaryKey:"CrossoverUpdatePublicKey") as? String,let key = Data(base64Encoded:text) else { throw UpdateProblem("The update signing information is missing.") }
                                let m = try verifiedManifest(manifestData,signature:signature,publicKey:key,bundleID:Bundle.main.bundleIdentifier ?? "")
                                guard UpdateVersion(m.version)! > UpdateVersion(self.version)!,UpdateVersion(m.build)! > UpdateVersion(self.build)!,UpdateVersion(m.version) == eligible.first?.0,let archive = asset(m.archive) else { throw UpdateProblem("The signed update does not match this release.") }
                                let os = ProcessInfo.processInfo.operatingSystemVersion
                                guard UpdateVersion("\(os.majorVersion).\(os.minorVersion).\(os.patchVersion)")! >= UpdateVersion(m.minimumSystemVersion)! else { throw UpdateProblem("This update requires macOS \(m.minimumSystemVersion) or later.") }
                                self.checking = false; UserDefaults.standard.set(Date(),forKey:"CrossoverLastUpdateCheck")
                                self.offer(m,archive:archive)
                            } catch { self.checkFailed(error,manual:manual) }
                        }
                    } catch { self.checkFailed(error,manual:manual) }
                }
            } catch { self.checkFailed(error,manual:manual) }
        }
    }
    func checkFailed(_ error: Error, manual: Bool) { checking = false; if manual { showMessage("Couldn't check for updates",error.localizedDescription) } }
    func offer(_ m: UpdateManifest, archive: URL) {
        #if UPDATER_TEST
        if (ProcessInfo.processInfo.environment["CROSSOVER_UPDATE_TEST"] == "install" || Bundle.main.object(forInfoDictionaryKey:"CrossoverTestInstall") as? Bool == true) { begin(m,archive:archive); return }
        #endif
        let alert = NSAlert()
        alert.messageText = m.important ? "Important update: \(m.version)" : "\(m.version) is available"
        alert.informativeText = m.notes + "\n\nThe app will download the update and reopen. Your saved settings and account are kept."
        alert.addButton(withTitle:"Update Now"); alert.addButton(withTitle:"Later")
        if alert.runModal() == .alertFirstButtonReturn { begin(m,archive:archive) }
    }
    func progress(_ text: String) {
        #if UPDATER_TEST
        if (ProcessInfo.processInfo.environment["CROSSOVER_UPDATE_TEST"] != nil || Bundle.main.object(forInfoDictionaryKey:"CrossoverTestInstall") as? Bool == true) { updateTestLog(text); return }
        #endif
        if panel == nil {
            let w = NSWindow(contentRect:NSRect(x:0,y:0,width:470,height:160),styleMask:[.titled,.closable],backing:.buffered,defer:false)
            w.title = "Updating \(Bundle.main.object(forInfoDictionaryKey:"CFBundleName") as? String ?? "Crossover")"; w.isReleasedWhenClosed = false; w.delegate = self
            let label = NSTextField(wrappingLabelWithString:text); label.frame = NSRect(x:24,y:65,width:422,height:70); w.contentView?.addSubview(label); status = label
            let button = NSButton(title:"Cancel",target:self,action:#selector(cancelUpdate)); button.bezelStyle = .rounded; button.frame = NSRect(x:350,y:18,width:96,height:32); w.contentView?.addSubview(button); cancelButton = button
            panel = w; w.center(); w.makeKeyAndOrderFront(nil)
        }
        status?.stringValue = text; cancelButton?.isEnabled = !replacing
    }
    public func windowShouldClose(_ sender: NSWindow) -> Bool { if replacing { return false }; cancelUpdate(); return true }
    @objc func cancelUpdate() {
        guard !replacing else { return }
        operation = UUID(); fetch?.cancel(); wait?.invalidate(); wait = nil; updating = false
        panel?.orderOut(nil); panel = nil; cleanup()
    }
    func cleanup() { for path in temporary { try? FileManager.default.removeItem(at:path) }; temporary = [] }
    func fail(_ error: Error) { replacing = false; cancelUpdate(); showMessage("The app wasn't updated",error.localizedDescription) }
    func whenIdle(_ id: UUID, action: @escaping () -> Void) {
        guard operation == id else { return }
        if !busy { action(); return }
        progress("Quit Dungeons and finish sign-in or setup. The update will continue automatically.")
        wait?.invalidate()
        wait = Timer.scheduledTimer(withTimeInterval:15,repeats:true) { timer in
            if self.operation != id { timer.invalidate(); return }
            if !self.busy { timer.invalidate(); self.wait = nil; action() }
        }; wait?.tolerance = 5
    }
    func begin(_ m: UpdateManifest, archive: URL) {
        updating = true; operation = UUID(); let id = operation
        whenIdle(id) {
            self.progress("Downloading \(m.version)…")
            self.fetch = UpdateFetch(url:archive,source:self.source,limit:m.bytes) { result in
                if self.operation != id { if case .success(let file) = result { try? FileManager.default.removeItem(at:file.deletingLastPathComponent()) }; return }
                do {
                    let file = try result.get(); self.temporary.append(file.deletingLastPathComponent()); self.progress("Verifying the update…")
                    DispatchQueue.global(qos:.utility).async {
                        do {
                            let staged = try self.prepare(file,m:m)
                            DispatchQueue.main.async {
                                if self.operation != id { try? FileManager.default.removeItem(at:staged); return }
                                self.temporary.append(staged)
                                self.whenIdle(id) { self.replace(staged,m:m) }
                            }
                        } catch { DispatchQueue.main.async { if self.operation == id { self.fail(error) } } }
                    }
                } catch { self.fail(error) }
            }
        }
    }
    func prepare(_ file: URL, m: UpdateManifest) throws -> URL {
        let bytes = try Data(contentsOf:file,options:.mappedIfSafe)
        guard Int64(bytes.count) == m.bytes,SHA256.hash(data:bytes).map({ String(format:"%02x",$0) }).joined() == m.sha256.lowercased() else { throw UpdateProblem("The download doesn't match its signed checksum.") }
        let parent = current.deletingLastPathComponent()
        guard !current.path.contains("/AppTranslocation/"),FileManager.default.isWritableFile(atPath:parent.path),FileManager.default.isWritableFile(atPath:current.path) else { throw UpdateProblem("This app is in a read-only location. Move it to your Applications folder before updating.") }
        let unpack = file.deletingLastPathComponent().appendingPathComponent("unpacked")
        try FileManager.default.createDirectory(at:unpack,withIntermediateDirectories:false)
        _ = try updateRun("/usr/bin/ditto",["-x","-k",file.path,unpack.path])
        let new = unpack.appendingPathComponent(current.lastPathComponent)
        guard new.resolvingSymlinksInPath().deletingLastPathComponent() == unpack.resolvingSymlinksInPath(),
              let bundle = Bundle(url:new),bundle.bundleIdentifier == m.bundleIdentifier,
              bundle.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String == m.version,
              bundle.object(forInfoDictionaryKey:"CFBundleVersion") as? String == m.build else { throw UpdateProblem("The download contains a different app or version.") }
        _ = try updateRun("/usr/bin/codesign",["--verify","--deep","--strict",new.path])
        let staged = parent.appendingPathComponent(".crossover-update-"+UUID().uuidString+".app")
        do {
            _ = try updateRun("/usr/bin/ditto",[new.path,staged.path])
            _ = try updateRun("/usr/bin/codesign",["--verify","--deep","--strict",staged.path]); return staged
        } catch { try? FileManager.default.removeItem(at:staged); throw error }
    }
    func replace(_ staged: URL, m: UpdateManifest) {
        replacing = true; progress("Installing \(m.version) and reopening…")
        guard renamex_np(current.path,staged.path,UInt32(RENAME_SWAP)) == 0 else { fail(UpdateProblem("macOS could not replace this app. The original app is unchanged.")); return }
        // staged is now the old app. Never include it in generic temporary cleanup.
        temporary.removeAll { $0 == staged }
        let receipt = FileManager.default.temporaryDirectory.appendingPathComponent("crossover-relaunch-"+UUID().uuidString)
        do {
            try FileManager.default.createDirectory(at:receipt,withIntermediateDirectories:false,attributes:[.posixPermissions:0o700])
            let info: [String:Any] = ["app":current.path,"backup":staged.path,"build":m.build,"pid":Int(getpid())]
            try JSONSerialization.data(withJSONObject:info).write(to:receipt.appendingPathComponent("receipt.json"),options:.atomic)
        } catch { rollback(staged,receipt:receipt); return }
        let config = NSWorkspace.OpenConfiguration(); config.createsNewApplicationInstance = true
        config.arguments = ["--crossover-updated",receipt.path]
        #if UPDATER_TEST
        config.environment = ["CROSSOVER_UPDATE_TEST":"relaunch"]
        #endif
        NSWorkspace.shared.openApplication(at:current,configuration:config) { app,error in
            DispatchQueue.main.async {
                guard app != nil,error == nil else { self.rollback(staged,receipt:receipt); return }
                var attempts = 0
                self.wait = Timer.scheduledTimer(withTimeInterval:0.25,repeats:true) { timer in
                    attempts += 1
                    if FileManager.default.fileExists(atPath:receipt.appendingPathComponent("ready").path) {
                        timer.invalidate(); self.wait = nil; self.replacing = false; self.updating = false; self.cleanup(); NSApp.terminate(nil)
                    } else if attempts >= 80 {
                        timer.invalidate(); self.wait = nil; app?.terminate(); self.rollback(staged,receipt:receipt)
                    }
                }
            }
        }
    }
    func rollback(_ backup: URL, receipt: URL) {
        if renamex_np(current.path,backup.path,UInt32(RENAME_SWAP)) == 0 { try? FileManager.default.removeItem(at:backup) }
        else { showMessage("The previous app was preserved","Recovery copy: \(backup.path)") }
        try? FileManager.default.removeItem(at:receipt)
        fail(UpdateProblem("The new app could not confirm it started. The previous version was kept."))
    }
    func acknowledgeRelaunch() -> Bool {
        guard let index = CommandLine.arguments.firstIndex(of:"--crossover-updated"),index+1 < CommandLine.arguments.count else { return false }
        let receipt = URL(fileURLWithPath:CommandLine.arguments[index+1]).standardizedFileURL
        guard receipt.deletingLastPathComponent().resolvingSymlinksInPath() == FileManager.default.temporaryDirectory.resolvingSymlinksInPath(),receipt.lastPathComponent.hasPrefix("crossover-relaunch-"),
              let data = try? Data(contentsOf:receipt.appendingPathComponent("receipt.json")),let row = try? JSONSerialization.jsonObject(with:data) as? [String:Any],
              row["app"] as? String == current.path,row["build"] as? String == build,let path = row["backup"] as? String,let pid = row["pid"] as? Int,pid > 0 else { return false }
        let backup = URL(fileURLWithPath:path).standardizedFileURL
        guard backup.deletingLastPathComponent() == current.deletingLastPathComponent(),backup.lastPathComponent.hasPrefix(".crossover-update-"),backup.pathExtension == "app" else { return false }
        DispatchQueue.main.async {
            try? Data("ready".utf8).write(to:receipt.appendingPathComponent("ready"),options:.atomic)
            #if UPDATER_TEST
            updateTestLog("Relaunch acknowledged: \(self.build)")
            #endif
            DispatchQueue.global(qos:.utility).async {
                for _ in 0..<40 { if kill(pid_t(pid),0) != 0 { break }; usleep(250000) }
                if kill(pid_t(pid),0) != 0 { try? FileManager.default.removeItem(at:backup); try? FileManager.default.removeItem(at:receipt) }
            }
        }
        return true
    }
}

#if UPDATER_TEST
func updateTestLog(_ text: String) {
    print("UPDATE: \(text)"); fflush(stdout)
    guard let path = Bundle.main.object(forInfoDictionaryKey:"CrossoverTestLog") as? String else { return }
    if !FileManager.default.fileExists(atPath:path) { FileManager.default.createFile(atPath:path,contents:nil) }
    if let file = FileHandle(forWritingAtPath:path) { defer { try? file.close() }; file.seekToEndOfFile(); file.write(Data((text+"\n").utf8)) }
}
#endif
