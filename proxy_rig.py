# ---------------------------------------------------------------------------- #
# Proxy rig toggle 
# ---------------------------------------------------------------------------- #
# Imports # reload(proxy_rig_toggle)

from maya import cmds, mel
import os


# ---------------------------------------------------------------------------- #
# Helper class for better dictionaries

class Vividict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value

# ---------------------------------------------------------------------------- #
# Retrieving settings

def _get_proxy_location_setting():
    if cmds.optionVar(exists='proxy_rig'):
        settings = cmds.optionVar(q='proxy_rig')
        if settings:
            return settings
    return ''


# ---------------------------------------------------------------------------- #
# Storing settings

def _store_proxy_location(path_to_proxy=None):
    if path_to_proxy:
        cmds.optionVar(sv=('proxy_rig', path_to_proxy))
    else:
        cmds.optionVar(remove='proxy_rig')
        

# ---------------------------------------------------------------------------- #
# Creating new settings

def user_set_proxy_folder(namespace, proxy_folder = None):

    if not proxy_folder:
        character_rig_file = cmds.referenceQuery(namespace + 'RN', filename=True)
        proxy_folder = os.path.dirname(character_rig_file)
        if not namespace:
            namespace = os.path.basename(character_rig_file)
    
    if not os.path.isdir(proxy_folder): # JUST IN CASE
        proxy_folder = 'C:\\'
    
    proxy_file = False
    try:
        proxy_file = cmds.fileDialog2(cap="Locate proxy file " + namespace + PROXY_FILE_SUFFIX, dialogStyle=2, dir=proxy_folder, fm=1)[0]
        print("Loading {}".format(proxy_file))
        if os.path.isfile(proxy_file):
            proxy_folder = os.path.dirname(proxy_file)
    except TypeError:
        print("Canceled!")
        return None

    if proxy_folder:
        return proxy_folder

    
# ---------------------------------------------------------------------------- #
# Globals

PROXY_FILE_SUFFIX = '_Proxy.ma'
PXM               = ':PXM'
RIG_GROUP         = ':Rig_GRP'
PROXY_GROUP       = ':Proxy_GRP'
TAG_ATTR          = 'tag'
ATTR_RIG_PATH     = 'rigPath'
ALL_ATTR          = 'trs_shot.All'
FACE_ATTR         = 'trs_shot.Face'
CONTROL_GROUP     = ':rig'
MESH_GROUP        = ':model'
ACCEPTED_PROXY_FILE_TYPES = ['mayaBinary', 'mayaAscii']


# ---------------------------------------------------------------------------- #
# Public methods

def install_proxy_rig():
    '''Toggle the group and the character'''
    
    PROXY_FOLDER = _get_proxy_location_setting()

    sel, data = _get_sel_namespaces()
    if not sel: return

    for namespace in data.keys():
        
        namespace_PXM = namespace + PXM
        
        long_namespace = data[namespace]['full_ref']
        
        if cmds.namespace(exists = namespace_PXM):
            cmds.warning("Proxy already exists for {}".format(namespace))
            return
        
        character_rig_file = cmds.referenceQuery(namespace + 'RN', filename=True, shortName=True)
        
        character_ID = os.path.splitext(character_rig_file)[0]
        
        # Might be the first time we use this:
        if not PROXY_FOLDER:
            # Check to see if proxy is in same spot as the rig file:
            character_rig_file_long = cmds.referenceQuery(namespace + 'RN', filename=True)
            file_name, file_ext     = os.path.splitext(os.path.basename(character_rig_file_long))
            folder_name             = os.path.dirname(character_rig_file_long)
            file_name_proxy = file_name + PROXY_FILE_SUFFIX
            proxy_rig_file = os.path.join(folder_name, file_name_proxy)
            # Assuming it found the proxy rig file in the same folder, check to see if it exists
            if os.path.isfile(proxy_rig_file):
                PROXY_FOLDER = folder_name
            else:
                # If not, just let the user point to it
                PROXY_FOLDER = user_set_proxy_folder(namespace)
                if PROXY_FOLDER:
                    _store_proxy_location(PROXY_FOLDER)
                else:
                    return None

        proxy_rig_file = os.path.join(PROXY_FOLDER, character_ID + PROXY_FILE_SUFFIX)
        
        print("Looking for proxy file at:\n{}".format(PROXY_FOLDER))
        
        # If the file doesn't exist, force the user to find it
        if not os.path.isfile(proxy_rig_file):
            print("Could not find proxy file. Please specify.")
            PROXY_FOLDER = user_set_proxy_folder(namespace)
            _store_proxy_location(PROXY_FOLDER)
        proxy_rig_file = os.path.join(PROXY_FOLDER, character_ID + PROXY_FILE_SUFFIX)
        
        # Get the file
        if os.path.isfile(proxy_rig_file):
            proxy_rig_file_type = cmds.file(proxy_rig_file, q=True, typ=True) or []
            if not proxy_rig_file_type: return None
            for file_type in ACCEPTED_PROXY_FILE_TYPES:
                if file_type in proxy_rig_file_type:
                    print("Proxy exists! Fetching...")
                    cmds.file(proxy_rig_file, r=True, namespace='{0}{1}'.format(namespace, PXM), mergeNamespacesOnClash=False, options="v=0")
                    break
        else:
            cmds.confirmDialog(
                title="Oh noes!",
                message="{} is not a valid proxy file.".format(proxy_rig_file),
                button="Ok, bye..."
            )
            return

        # Get the pieces
        character_ID_proxyGRP = namespace + PXM + PROXY_GROUP
        if not cmds.objExists(character_ID_proxyGRP):
            cmds.error("Something went terribly wrong. Could not find proxy group!")
            return
        
        proxy_pieces = cmds.listRelatives(character_ID_proxyGRP) or []
        if not proxy_pieces:
            cmds.error("Something went terribly wrong. Could not find proxy pieces!")
            return # I don't even know how this would be possible, but just in case...

        # Attach the pieces
        for proxy_piece in proxy_pieces:
            raw_joint = proxy_piece.split(':')[-1].replace('proxy_', '')
            character_joint = long_namespace + ':' + raw_joint
            cmds.parentConstraint(character_joint, proxy_piece)

        cmds.setAttr(character_ID_proxyGRP + '.v', 0)
        
        VIS_DATA = Vividict()
        try:
            controls = cmds.listRelatives(namespace + CONTROL_GROUP)
            meshes = cmds.listRelatives(namespace + MESH_GROUP)

            for control in controls:
                VIS_DATA[namespace][control] = cmds.getAttr(control + '.v')
                if VIS_DATA[namespace][control]:
                    VIS_DATA[namespace][control] = cmds.getAttr(control + '.v', settable=True)
            for mesh in meshes:
                VIS_DATA[namespace][mesh] = cmds.getAttr(mesh + '.v')
                if VIS_DATA[namespace][mesh]:
                    VIS_DATA[namespace][mesh] = cmds.getAttr(mesh + '.v', settable=True)
            VIS_DATA[namespace][namespace + ':' + FACE_ATTR] = cmds.getAttr(namespace + ':' + FACE_ATTR)
            VIS_DATA[namespace][namespace + ':' + ALL_ATTR] = cmds.getAttr(namespace + ':' + ALL_ATTR)
            
        except ValueError:
            cmds.warning('This rig not supported by the proxy_rig script')
        finally:
            cmds.addAttr(character_ID_proxyGRP, longName="VISDATA", dt="string")
            cmds.setAttr(character_ID_proxyGRP + '.VISDATA', str(VIS_DATA), type="string")

    cmds.select(sel)
    
    return True

    
def toggle_proxy_rig(**kwargs):
    '''Toggle the group and the character'''
    
    sel, data = _get_sel_namespaces()
    if not sel: return
    
    proxy_group = None
    override = False

    for namespace in data.keys():
        if namespace in PXM:
            pxm_namespace = data[namespace]['full_ref']
            proxy_group = pxm_namespace + PROXY_GROUP
        else:
            if cmds.objExists(namespace + PXM + PROXY_GROUP):
                proxy_group = namespace + PXM + PROXY_GROUP

        if not proxy_group:
            cmds.warning("No proxies found for {0}".format(namespace))
            # continue
            if not 'override_vis' in kwargs: # Install it if you can't find it? Might lead to spam...
                success = install_proxy_rig()
                if not success:
                    return None
            else:
                continue
            proxy_group = namespace + PXM + PROXY_GROUP


        # Delete keys on the .Face attr
        try:
            if cmds.getAttr(namespace + ':' + FACE_ATTR, settable=True):
                if cmds.getAttr(namespace + ':' + FACE_ATTR, keyable=True):
                    cmds.cutKey(namespace + ':' + FACE_ATTR)
        except:
            pass # Maybe no .Face attr?

        # Delete keys on the .All attr
        try:
            if cmds.getAttr(namespace + ':' + ALL_ATTR, settable=True):
                if cmds.getAttr(namespace + ':' + ALL_ATTR, keyable=True):
                    cmds.cutKey(namespace + ':' + ALL_ATTR)
        except:
            pass # Maybe no .All attr?

        if 'override_vis' in kwargs:
            vis = not kwargs.pop('override_vis')
            override = True
            print("Override found - setting proxy to {}".format(vis))
        else:
            vis = cmds.getAttr(proxy_group + '.v')
        
        KYOSIL_RIG = False
        try:
            controls = cmds.listRelatives(namespace + CONTROL_GROUP)
            meshes = cmds.listRelatives(namespace + MESH_GROUP)
            KYOSIL_RIG = True
        except ValueError:
            KYOSIL_RIG = False
        
        # Get vis vis_attr
        try:
            vis_attr = cmds.getAttr(proxy_group + '.VISDATA')
            VIS_DATA = eval(vis_attr)
            if KYOSIL_RIG:
                for control in controls:
                    if VIS_DATA[namespace][control]:
                        cmds.setAttr(control + '.v', vis)
                for mesh in meshes:
                    if VIS_DATA[namespace][mesh]:
                        cmds.setAttr(mesh + '.v', vis)
                if VIS_DATA[namespace][namespace + ':' + FACE_ATTR]:
                    cmds.setAttr(namespace + ':' + FACE_ATTR, int(vis))
                    if vis == 1:
                        VIS_DATA[namespace][namespace + ':' + FACE_ATTR] = cmds.getAttr(namespace + ':' + FACE_ATTR)
                if VIS_DATA[namespace][namespace + ':' + ALL_ATTR]:
                    cmds.setAttr(namespace + ':' + ALL_ATTR, int(vis))
                    if vis == 1:
                        VIS_DATA[namespace][namespace + ':' + ALL_ATTR] = cmds.getAttr(namespace + ':' + ALL_ATTR)
                # Save the settings we switched
                character_ID_proxyGRP = namespace + PXM + PROXY_GROUP    
                cmds.setAttr(character_ID_proxyGRP + '.VISDATA', str(VIS_DATA), type="string")
        except: 
            if KYOSIL_RIG:
                if override:
                    for control in controls:
                        try:
                            cmds.setAttr(control + '.v', vis)
                        except: continue
                    for mesh in meshes:
                        try:
                            cmds.setAttr(mesh + '.v', vis)
                        except: continue
                    cmds.setAttr(namespace + ':' + FACE_ATTR, int(vis))
                    cmds.setAttr(namespace + ':' + ALL_ATTR, int(vis))
        
        cmds.setAttr(proxy_group + '.v', not vis)
        if vis:
            print("{} proxy mode - DISABLED".format(namespace))
        else:
            print("{} proxy mode - ENABLED".format(namespace))
        


def toggle_proxy_section(section):
    '''Hiding via tags'''

    sel, data = _get_sel_namespaces()
    if not sel: return
    
    proxy_pieces = []
    
    for namespace in data.keys():
        if cmds.objExists(namespace + ":Proxy" + PROXY_GROUP):
            proxy_pieces = cmds.listRelatives(namespace + ":Proxy" + PROXY_GROUP)
        elif cmds.objExists(namespace + PXM + PROXY_GROUP):
            proxy_pieces = cmds.listRelatives(namespace + PXM + PROXY_GROUP)
        elif cmds.objExists(PXM + PROXY_GROUP):
            proxy_pieces = cmds.listRelatives(PXM + PROXY_GROUP)
        
        if not proxy_pieces: 
            cmds.warning("No proxies found for {0}".format(namespace))
            return

        for piece in proxy_pieces:
            ud_attrs = cmds.listAttr(piece, userDefined=True) or []
            if TAG_ATTR in ud_attrs:
                if section in cmds.getAttr(piece + '.' + TAG_ATTR):
                    cmds.setAttr(piece + '.v', not cmds.getAttr(piece + '.v'))
    

def set_tag(tag=None):
    '''Add tag label to selected objects'''
    if not tag: 
        cmds.error("Must pass tag<str> to label selected objects")
        return
    
    sel, data = _get_sel_namespaces()
    
    if not sel: return

    for namespace in data.keys():
        if cmds.objExists(namespace + ":Proxy" + PROXY_GROUP):
            proxy_pieces = cmds.listRelatives(namespace + ":Proxy" + PROXY_GROUP)
        elif cmds.objExists(namespace + PXM + PROXY_GROUP):
            proxy_pieces = cmds.listRelatives(namespace + PXM + PROXY_GROUP)
        elif cmds.objExists(PXM + PROXY_GROUP):
            proxy_pieces = cmds.listRelatives(PXM + PROXY_GROUP)

        for piece in sel:
            if piece in proxy_pieces: # Make sure you're only tagging proxy things!
                try:
                    cmds.addAttr(piece, longName="tag", dt="string")
                except:
                    pass
                finally:
                    cmds.setAttr(piece + '.tag', tag, type="string")


def uninstall_proxy_rig():
    
    sel, data = _get_sel_namespaces()
    if not sel: return
    
    
    for namespace in data.keys():
        namespace_PXM = namespace + PXM
        
        if cmds.namespace(exists = namespace_PXM):
            try:
                toggle_proxy_rig(override_vis = False)
            except ValueError:
                cmds.warning('Unsupported proxy_rig detected... compensating...')
            proxy_rig_file = cmds.referenceQuery(namespace_PXM + 'RN', filename=True)
            
            cmds.file(proxy_rig_file, removeReference=True, force=True)
            
            # Then get rid of the parent constraints
            if cmds.objExists(namespace_PXM + 'RNfosterParent1'):
                cmds.delete(namespace_PXM + 'RNfosterParent1')

            # cmds.namespace( deleteNamespaceContent = True
            #               , removeNamespace = namespace_PXM
            #               )
        else:
            cmds.warning("Could not find proxy for {}".format(namespace))
    
    cmds.select(clear=True)
    for each in sel:
        if cmds.objExists(each):
            cmds.select(sel, add=True)

    
# ---------------------------------------------------------------------------- #
# Private methods

def _get_sel_namespaces():
    '''Return the namespaces of the selected objects'''
    sel = cmds.ls(sl=1, o=True) or []
    if not sel:
        cmds.warning("Must select something first")
        return None, None

    namespaces = set()
    data = Vividict()
        
    for each in sel:
        reference_node = cmds.referenceQuery(each, referenceNode=True)
        short_ref = cmds.referenceQuery(reference_node, namespace=True, shortName=True)
        full_ref = each.rpartition(':')[0]
        
        if each not in data[short_ref]['selection']:
            data[short_ref]['full_ref'] =  full_ref
        
        if not data[short_ref]['selection']:
            data[short_ref]['selection'] = []
        data[short_ref]['selection'].append(each)
        
        if each == short_ref:
            namespaces.add(':')
            continue

        namespaces.add(short_ref)
        
        # if short_ref != full_ref:
            
        # namespace = short_ref.split("Proxy")[0] # Get namespace
        # namespaces.add(namespace)
    
    # return sel, list(namespaces)
    return sel, data

# ---------------------------------------------------------------------------- #
# Developer Section     

if __name__ == '__main__':
    toggle_proxy_rig()
    # uninstall_proxy_rig()

# EoF
