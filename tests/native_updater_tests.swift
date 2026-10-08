import Foundation
import CryptoKit
@main struct Tests {
 static func main() throws {
  func v(_ s: String) -> UpdateVersion { UpdateVersion(s)! }
  precondition(v("1.10.0") > v("1.9.2")); precondition(v("0.1.1-preview.10") > v("0.1.1-preview.2"))
  precondition(v("0.1.1") > v("0.1.1-preview.10")); precondition(v("1.0") == v("1.0.0"))
  precondition(UpdateVersion("dev") == nil); precondition(UpdateVersion("1..2") == nil); precondition(UpdateVersion("1.2-") == nil)
  precondition(updateGameName("C:\\Games\\Dungeons-Win64-Shipping.exe")); precondition(updateGameName("C:\\Games\\Dungeons-WinGDK-Shipping.exe")); precondition(!updateGameName("C:\\windows\\explorer.exe"))
  let source = UpdateSource(repository:"Wanzho/mcd1-crossover")
  precondition(source.asset(URL(string:source.root+"v1.0/app.zip")!)); precondition(!source.asset(URL(string:"https://github.com/other/project/releases/download/v1/app.zip")!))
  precondition(!source.allowed(URL(string:"https://github.com.evil.test/app.zip")!)); precondition(!source.allowed(URL(string:"http://github.com/app.zip")!))
  precondition(!source.asset(URL(string:source.root+"v1/app.zip?redirect=1")!))
  let key = Curve25519.Signing.PrivateKey()
  let m = UpdateManifest(schema:1,bundleIdentifier:"test",version:"0.1.1-preview.1",build:"16.4",archive:"update.zip",bytes:42,sha256:String(repeating:"a",count:64),minimumSystemVersion:"13.0",notes:"Test",important:true)
  let data = try JSONEncoder().encode(m), signature = try key.signature(for:data)
  let verified = try verifiedManifest(data,signature:signature,publicKey:key.publicKey.rawRepresentation,bundleID:"test"); precondition(verified.important)
  func refuses(_ d: Data, _ s: Data, _ id: String) {
   do { _ = try verifiedManifest(d,signature:s,publicKey:key.publicKey.rawRepresentation,bundleID:id); fatalError("Accepted invalid manifest") } catch {}
  }
  refuses(data+Data(" ".utf8),signature,"test"); refuses(data,signature,"another-app")
  refuses(data,Data(repeating:0,count:64),"test")
  let bad = UpdateManifest(schema:1,bundleIdentifier:"test",version:"1",build:"1",archive:"../update.zip",bytes:42,sha256:String(repeating:"a",count:64),minimumSystemVersion:"13.0",notes:"Test",important:false)
  let badData = try JSONEncoder().encode(bad); refuses(badData,try key.signature(for:badData),"test")
  print("PASS: version ordering, previews, Wine names, download origin, signatures, tampering, app identity and archive paths")
 }
}
