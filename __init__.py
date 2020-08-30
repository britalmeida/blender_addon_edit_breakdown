# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

bl_info = {
    "name": "Edit Breakdown",
    "author": "Inês Almeida, Francesco Siddi",
    "version": (0, 1, 0),
    "blender": (2, 90, 0),
    "location": "Video Sequence Editor",
    "description": "Get insight on the complexity of an edit",
    "doc_url": "https://github.com/britalmeida/blender_addon_edit_breakdown",
    "category": "Sequencer",
}

import logging
import math
import os

import bpy
from bpy_extras.image_utils import load_image
from bpy.types import AddonPreferences, Operator, Panel, PropertyGroup
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, StringProperty, PointerProperty

if "draw_utils" in locals():
    import importlib

    importlib.reload(draw_utils)
else:
    from . import draw_utils

log = logging.getLogger(__name__)


# Data ########################################################################

class SEQUENCER_EditBreakdown_Shot(PropertyGroup):
    """Properties of a shot."""

    shot_name: StringProperty(name="Shot Name")
    frame_start: IntProperty(name="Frame")
    duration: IntProperty(name="Duration", description="Number of frames in this shot")
    character_count: IntProperty(name="Character Count")
    animation_complexity: EnumProperty(name="Anim Complexity",
        items=[('1', '1', '1'), ('2', '2', '2'), ('3', '3', '3'), ('4', '4', '4'), ('5', '5', '5')])
    has_fx: BoolProperty(name="Has Effects")
    has_crowd: BoolProperty(name="Has Crowd")
    thumbnail_image = None


class SEQUENCER_EditBreakdown_Data(PropertyGroup):

    shots: CollectionProperty(
        type=SEQUENCER_EditBreakdown_Shot,
        name="Shots",
        description="Set of shots that form the edit",
    )

    total_shot_duration = 0


# Operators ###################################################################

class SEQUENCER_OT_sync_edit_breakdown(Operator):
    bl_idname = "sequencer.sync_edit_breakdown"
    bl_label = "Sync Edit Breakdown"
    bl_description = "Ensure the edit breakdown is up-to-date with the edit"
    bl_options = {'REGISTER'}

    def calculate_shots_duration(self, context):
        shots = context.scene.edit_breakdown.shots

        total_duration_frames = 0
        last_frame = max(context.scene.frame_end, shots[-1].frame_start)
        for shot in reversed(shots):
            shot.duration = last_frame - shot.frame_start
            last_frame = shot.frame_start
            total_duration_frames += shot.duration

        context.scene.edit_breakdown.total_shot_duration = total_duration_frames
        # WIP
        fps = 30
        total_seconds = total_duration_frames/fps
        log.info(f"Edit has {total_seconds:.1f} seconds, with a total of {total_duration_frames} frames")

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        """Called to finish this operator's action.

        Recreate the edit breakdown data based on the current edit.
        """

        log.debug("sync_edit_breakdown: execute")

        sequence_ed = context.scene.sequence_editor
        addon_prefs = context.preferences.addons[__name__].preferences
        shots = context.scene.edit_breakdown.shots

        # Clear the previous breakdown data
        thumbnail_images.clear()
        shots.clear()

        # Load data from the sequence markers marked for use in the edit breakdown
        def WIP_fake_behaviour():
            load_edit_thumbnails()
            for img in thumbnail_images:
                new_shot = shots.add()
                new_shot.shot_name = str(img.name)
                new_shot.frame_start = img.name
                new_shot.thumbnail_image = img
        WIP_fake_behaviour()

        self.calculate_shots_duration(context)

        # Position the images according to the available space.
        fit_thumbnails_in_region()

        return {'FINISHED'}



# UI ##############################################################################################


class SEQUENCER_PT_edit_breakdown_overview(Panel):
    bl_label = "Overview"
    bl_category = "Edit Breakdown"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'IMAGE_EDITOR'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        edit_breakdown = context.scene.edit_breakdown

        col = layout.column()
        col.label(text=f"Shots: {len(edit_breakdown.shots)}")

        total_duration_frames = edit_breakdown.total_shot_duration
        total_duration_frames = 14189
        # WIP
        fps = 30
        total_seconds = total_duration_frames/fps
        col.label(text=f"Frames: {total_duration_frames}")
        col.label(text=f"Duration: {total_seconds/60:.1f} min ({total_seconds:.0f} seconds)")


class SEQUENCER_PT_edit_breakdown_shot(Panel):
    bl_label = "Shot"
    bl_category = "Edit Breakdown"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'IMAGE_EDITOR'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        selected_shot = context.scene.edit_breakdown.shots[0] # WIP

        col = layout.column()
        col.prop(selected_shot, "shot_name")
        sub = col.column()
        sub.enabled = False
        sub.prop(selected_shot, "duration", text="Num Frames")
        # WIP
        fps = 30
        total_seconds = selected_shot.duration/fps
        col.label(text=f"Duration: {total_seconds/60:.1f} min ({total_seconds:.0f} seconds)")
        col.prop(selected_shot, "animation_complexity")
        col.prop(selected_shot, "character_count")
        col.prop(selected_shot, "has_crowd")
        col.prop(selected_shot, "has_fx")


def draw_sequencer_header_extension(self, context):
    layout = self.layout
    layout.operator("sequencer.sync_edit_breakdown", icon='SEQ_SPLITVIEW') #FILE_REFRESH


def draw_background():
    region = bpy.context.region
    draw_utils.draw_background((region.width, region.height))


# Drawing Thumbnail Images ########################################################################

class ThumbnailImage:
    """Displayed thumbnail data"""

    id_image = None # A Blender ID Image, which can be rendered by bgl.
    pos = (0, 0) # Position in px where the image should be displayed within a region.
    name = ""

thumbnail_images = [] # All the loaded thumbnails for an edit.
thumbnail_size = (0, 0) # The size in px at which the thumbnails should be displayed.


def load_edit_thumbnails():
    """Load all images from disk as resources to be rendered by the GPU"""

    addon_prefs = bpy.context.preferences.addons[__name__].preferences
    folder_name = addon_prefs.edit_shots_folder

    try:
        for filename in os.listdir(folder_name):
            img = ThumbnailImage()
            img.id_image = load_image(filename,
                dirname=folder_name,
                place_holder=False,
                recursive=False,
                ncase_cmp=True,
                convert_callback=None,
                verbose=False,
                relpath=None,
                check_existing=True,
                force_reload=False)
            thumbnail_images.append(img)
            img.name = int(filename.split('.')[0])
    except FileNotFoundError:
        # self.report({'ERROR'}, # Need an operator
        log.warning(
            f"Reading thumbnail images from '{folder_name}' failed: folder does not exist.")

    thumbnail_images.sort(key=lambda x: x.name, reverse=False)

    for img in thumbnail_images:
        if img.id_image.gl_load():
            raise Exception()

    num_images = len(thumbnail_images)
    log.info(f"Loaded {num_images} images.")


def fit_thumbnails_in_region():
    """Calculate the thumbnails' size and where to render each one so they fit the given region

    The thumbnail size is roughly calculated by dividing the available region area by the number
    of images and preserving the image aspect ratio. However, this calculation will be off as
    soon as the images don't exactly fit a row or the last row is incomplete.
    To account for that, we take some space away from the region area, which will be used by
    margins and spacing between images. The thumbnail size is calculated to fit the smaller area.
    This way, images can be made to exactly fit a row by taking up whitespace.
    """

    # If there are no images to fit, we're done!
    num_images = len(thumbnail_images)
    if num_images == 0:
        return

    log.debug("------Fit Images-------------------");

    global thumbnail_size

    # Get size of the region containing the thumbnails.
    region = bpy.context.region
    total_available_w = region.width
    total_available_h = region.height
    start_w = 0 # If the tools side panel is open, the thumbnails must be shifted to the right
    # If the header and side panels render on top of the region, discount their size.
    # The thumbnails should not be occluded by the UI, even if set to transparent.
    system_prefs = bpy.context.preferences.system
    if system_prefs.use_region_overlap:
        area = bpy.context.area
        for r in area.regions:
            if r.type == 'HEADER' and r.height > 1:
                total_available_h -= r.height
            if r.type == 'UI' and r.width > 1:
                total_available_w -= r.width
            if r.type == 'TOOLS' and r.width > 1:
                total_available_w -= r.width
                start_w = r.width

    log.debug(f"Region w:{total_available_w} h:{total_available_h}")

    # Get the available size, discounting white space size.
    total_spacing = (150, 150) 
    min_margin = 40 # Arbitrary 20px minimum for the top,bottom,left and right margins
    available_w = total_available_w - total_spacing[0]
    available_h = total_available_h - total_spacing[1]
    max_thumb_size = (total_available_w - min_margin, total_available_h - min_margin)

    # Get the original size and aspect ratio of the images.
    # Assume all images in the edit have the same aspect ratio.
    original_image_w = thumbnail_images[0].id_image.size[0]
    original_image_h = thumbnail_images[0].id_image.size[1]
    image_aspect_ratio = original_image_w / original_image_h
    log.debug(f"Image a.ratio={image_aspect_ratio:.2f} ({original_image_w}x{original_image_h})")

    # Calculate by how much images need to be scaled in order to fit. (won't be perfect)
    available_area = available_w * available_h
    thumbnail_area = available_area / num_images
    # If the pixel area gets very small, early out, not worth rendering.
    if thumbnail_area < 20:
        thumbnail_size = (0, 0)
        return
    scale_factor = math.sqrt(thumbnail_area / (original_image_w * original_image_h))
    log.debug(f"Scale factor: {scale_factor:.3f}");
    thumbnail_size = (original_image_w * scale_factor,
                      original_image_h * scale_factor)

    num_images_per_row = math.ceil(available_w / thumbnail_size[0])
    num_images_per_col = math.ceil(num_images / num_images_per_row)
    log.debug(f"Thumbnail width  {thumbnail_size[0]:.3f}px, # per row: {num_images_per_row:.3f}")
    log.debug(f"Thumbnail height {thumbnail_size[1]:.3f}px, # per col: {num_images_per_col:.3f}")

    # Make sure that both a row and a column of images at the current scale will fit.
    # It is possible that, with few images and a region aspect ratio that is very different from
    # the images', there is enough area, but not enough length in one direction.
    # In that case, reduce the thumbnail size further.
    if original_image_w * scale_factor * num_images_per_row > max_thumb_size[0]:
        scale_factor = max_thumb_size[0] / (original_image_w * num_images_per_row)
    if original_image_h * scale_factor * num_images_per_col > max_thumb_size[1]:
        scale_factor = max_thumb_size[1] / (original_image_h * num_images_per_col)
    log.debug(f"Reduced scale factor: {scale_factor:.3f}");

    thumbnail_size = (original_image_w * scale_factor,
                      original_image_h * scale_factor)

    # Get the remaining space not occupied by thumbnails and split it into margins
    # and spacing between the thumbnails.
    def calculate_spacing(total_available, thumb_size, num_thumbs):

        available_space = total_available - thumb_size * num_thumbs
        log.debug(f"remaining space {available_space:.2f}px")

        spacing = 0
        if num_thumbs > 1:
            spacing = (available_space - min_margin) / (num_thumbs - 1)
            log.debug(f"spacing={spacing:.3f}")
            # Spacing between images should never be bigger than the margins
            spacing = min(math.ceil(spacing), min_margin)

        margin = (available_space - spacing * (num_thumbs - 1)) / 2
        log.debug(f"margins={margin:.3f}")
        margin = math.floor(margin)

        return (margin, spacing)

    log.debug(f"X")
    space_w = calculate_spacing(total_available_w, thumbnail_size[0], num_images_per_row)
    log.debug(f"Y")
    space_h = calculate_spacing(total_available_h, thumbnail_size[1], num_images_per_col)

    margins = (space_w[0], space_h[0])
    spacing = (space_w[1], space_h[1])

    # Set the position of each thumbnail
    start_pos_x = start_w + margins[0]
    start_pos_y = total_available_h - thumbnail_size[1] - margins[1]
    last_start_pos_x = start_w + math.ceil(margins[0] + (num_images_per_row - 1)* (thumbnail_size[0] + spacing[0]))

    for img in thumbnail_images:
        img.pos = (start_pos_x, start_pos_y)
        start_pos_x += thumbnail_size[0] + spacing[0]
        # Next row
        if start_pos_x > last_start_pos_x:
            start_pos_x = start_w + margins[0]
            start_pos_y -= thumbnail_size[1] + spacing[1]


def draw_edit_thumbnails():
    """Render the edit thumbnails"""

    # Load the images the first time they're needed.
    if not thumbnail_images:
        load_edit_thumbnails()

    # Position the images according to the available space.
    fit_thumbnails_in_region()

    # If the resulting layout makes the images too small, skip rendering.
    if thumbnail_size[0] <= 5 or thumbnail_size[1] <= 5:
        return

    # Render each image.
    draw_utils.draw_thumbnails(thumbnail_images, thumbnail_size)


def draw_overlay():
    """Draw overlay effects on top of the thumbnails"""

    #draw_utils.draw_overlay()
    pass


# Settings ####################################################################


class SEQUENCER_EditBreakdown_Preferences(AddonPreferences):
    bl_idname = __name__

    edit_shots_folder: StringProperty(
        name="Edit Shots",
        description="Folder with image thumbnails for each shot",
        default="",
        subtype="FILE_PATH"
    )

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.prop(self, "edit_shots_folder")


# Add-on Registration #########################################################

classes = (
    SEQUENCER_EditBreakdown_Preferences,
    SEQUENCER_EditBreakdown_Shot,
    SEQUENCER_EditBreakdown_Data,
    SEQUENCER_OT_sync_edit_breakdown,
    SEQUENCER_PT_edit_breakdown_overview,
    SEQUENCER_PT_edit_breakdown_shot,
)

draw_handles = []
space = bpy.types.SpaceImageEditor # SpaceSequenceEditor

def register():
    log.info("------Registering Edit Breakdown-------------------")

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TimelineMarker.use_for_edit_breakdown = BoolProperty(
        name="Use For Edit Breakdown",
        default=True,
        description="If this marker should be included as a shot in the edit breakdown view",
    )

    bpy.types.Scene.edit_breakdown = PointerProperty(
        name="Edit Breakdown",
        type=SEQUENCER_EditBreakdown_Data,
        description="Shot data used by the Edit Breakdown add-on.",
    )

    bpy.types.SEQUENCER_HT_header.append(draw_sequencer_header_extension)

    draw_handles.append(space.draw_handler_add(draw_background, (), 'WINDOW', 'POST_PIXEL'))
    draw_handles.append(space.draw_handler_add(draw_edit_thumbnails, (), 'WINDOW', 'POST_PIXEL'))
    draw_handles.append(space.draw_handler_add(draw_overlay, (), 'WINDOW', 'POST_PIXEL'))
    draw_handles.append(space.draw_handler_add(draw_utils.draw_text, (None, None), 'WINDOW', 'POST_PIXEL'))

    log.info("------Done Registering-----------------------------")


def unregister():

    log.info("------Unregistering Edit Breakdown-----------------")

    for handle in draw_handles:
        space.draw_handler_remove(handle, 'WINDOW')

    bpy.types.SEQUENCER_HT_header.remove(draw_sequencer_header_extension)

    del bpy.types.TimelineMarker.use_for_edit_breakdown
    del bpy.types.Scene.edit_breakdown

    for cls in classes:
        bpy.utils.unregister_class(cls)

    log.info("------Done Unregistering---------------------------")


if __name__ == "__main__":
    register()
