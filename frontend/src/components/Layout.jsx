import { Link } from 'react-router-dom'
import Navbar from './Navbar'
export default function Layout({ children }) { return <><Navbar /><main>{children}</main><footer><div><Link to="/" className="brand"><span className="brand-mark">FM</span><span>Farm<span>Market</span></span></Link><p>A more direct route from local soil to your table.</p></div><div className="footer-note">Built for growers, cooks, and good food.</div></footer></> }
